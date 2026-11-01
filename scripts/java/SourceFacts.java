import com.sun.source.tree.*;
import com.sun.source.util.JavacTask;
import com.sun.source.util.Trees;
import java.io.IOException;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.*;
import javax.tools.*;

/** Parse explicitly supplied Java sources; never analyze or execute project code. */
public final class SourceFacts {
    private static final String SPRING = "org.springframework.context.annotation.";
    private static final String WEB = "org.springframework.web.bind.annotation.";
    private static final Set<String> JAVA_LANG = Set.of("String", "Object", "Integer", "Long", "Boolean", "Double", "Float", "Short", "Byte", "Character", "Void");
    private final List<Map<String, Object>> types = new ArrayList<>();
    private final List<Map<String, Object>> producers = new ArrayList<>();
    private final List<Map<String, Object>> routes = new ArrayList<>();
    private final Set<String> gaps = new TreeSet<>();
    private final Set<String> declared = new HashSet<>();
    private final Set<String> duplicateTypes = new HashSet<>();
    private Trees trees;
    private boolean limitExceeded;

    private void addFact(List<Map<String, Object>> target, Map<String, Object> fact) {
        if (types.size() + producers.size() + routes.size() >= 1000) limitExceeded = true;
        else target.add(fact);
    }

    private static final class Scope {
        String pkg;
        Map<String, String> imports = new HashMap<>();
        Set<String> ambiguous = new HashSet<>();
        boolean wildcard;
        Set<String> shadows = new HashSet<>();
    }

    private Scope scope(CompilationUnitTree unit) {
        Scope s = new Scope();
        s.pkg = unit.getPackageName() == null ? "" : unit.getPackageName().toString();
        for (ImportTree imp : unit.getImports()) {
            if (imp.isStatic()) continue;
            String value = imp.getQualifiedIdentifier().toString();
            if (value.endsWith(".*")) { s.wildcard = true; continue; }
            String name = value.substring(value.lastIndexOf('.') + 1);
            String previous = s.imports.putIfAbsent(name, value);
            if (previous != null && !previous.equals(value)) s.ambiguous.add(name);
        }
        return s;
    }

    private String resolve(Tree tree, Scope s) {
        if (tree == null) return null;
        if (tree.getKind() != Tree.Kind.IDENTIFIER && tree.getKind() != Tree.Kind.MEMBER_SELECT) return null;
        String name = tree.toString();
        if (s.shadows.contains(name.contains(".") ? name.substring(0, name.indexOf('.')) : name)) return null;
        if (!name.matches("[A-Za-z_$][A-Za-z0-9_$]*(\\.[A-Za-z_$][A-Za-z0-9_$]*)*")) return null;
        if (name.contains(".")) {
            String first = name.substring(0, name.indexOf('.'));
            if (Character.isLowerCase(first.charAt(0))) {
                String[] parts = name.split("\\.");
                int typeParts = 0;
                for (String part : parts) if (!Character.isLowerCase(part.charAt(0))) typeParts++;
                return typeParts == 1 && !Character.isLowerCase(parts[parts.length - 1].charAt(0)) ? name : null;
            }
            return null; // nested names and ambiguous simple qualifiers
        }
        if (s.ambiguous.contains(name)) return null;
        String local = s.pkg.isEmpty() ? name : s.pkg + "." + name;
        if (duplicateTypes.contains(local)) return null;
        if (s.imports.containsKey(name)) return declared.contains(local) ? null : s.imports.get(name);
        if (declared.contains(local)) return s.wildcard ? null : local;
        if (JAVA_LANG.contains(name) && !s.wildcard) return "java.lang." + name;
        return null;
    }

    private boolean is(AnnotationTree a, Scope s, String expected) {
        return expected.equals(resolve(a.getAnnotationType(), s));
    }

    private AnnotationTree find(ModifiersTree mods, Scope s, String fq) {
        for (AnnotationTree a : mods.getAnnotations()) if (is(a, s, fq)) return a;
        return null;
    }

    private List<String> literals(ExpressionTree expr) {
        if (expr instanceof LiteralTree literal && literal.getValue() instanceof String value) return List.of(value);
        if (expr instanceof NewArrayTree array && array.getInitializers() != null) {
            List<String> values = new ArrayList<>();
            for (ExpressionTree item : array.getInitializers()) {
                if (!(item instanceof LiteralTree literal) || !(literal.getValue() instanceof String value)) return null;
                values.add(value);
            }
            return values;
        }
        return null;
    }

    private List<String> annotationNames(AnnotationTree annotation, String implicit) {
        if (annotation.getArguments().isEmpty()) return List.of(implicit);
        if (annotation.getArguments().size() != 1) return null;
        ExpressionTree arg = annotation.getArguments().get(0);
        if (arg instanceof AssignmentTree assign) {
            if (!Set.of("name", "value").contains(assign.getVariable().toString())) return null;
            arg = assign.getExpression();
        }
        List<String> names = literals(arg);
        if (names == null || names.isEmpty()) return null;
        for (String name : names) if (!name.matches("[A-Za-z_$][A-Za-z0-9_.$]*") || name.length() > 256) return null;
        return names;
    }

    private List<String> mappingPaths(AnnotationTree annotation) {
        if (annotation == null || annotation.getArguments().isEmpty()) return List.of("");
        if (annotation.getArguments().size() != 1) return null;
        ExpressionTree arg = annotation.getArguments().get(0);
        if (arg instanceof AssignmentTree assign) {
            if (!Set.of("value", "path").contains(assign.getVariable().toString())) return null;
            arg = assign.getExpression();
        }
        List<String> paths = literals(arg);
        if (paths == null || paths.isEmpty()) return null;
        for (String path : paths) if (!path.matches("[A-Za-z0-9_/{}/.-]*") || path.length() > 256) return null;
        return paths;
    }

    private List<String> requestMethods(ExpressionTree expression, Scope scope) {
        List<? extends ExpressionTree> expressions;
        if (expression instanceof NewArrayTree array && array.getInitializers() != null) expressions = array.getInitializers();
        else expressions = List.of(expression);
        List<String> result = new ArrayList<>();
        for (ExpressionTree item : expressions) {
            if (!(item instanceof MemberSelectTree member) || member.getExpression().getKind() != Tree.Kind.IDENTIFIER || !(WEB + "RequestMethod").equals(resolve(member.getExpression(), scope))) return null;
            String method = member.getIdentifier().toString();
            if (!Set.of("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE").contains(method)) return null;
            result.add(method);
        }
        return result.isEmpty() ? null : result;
    }

    private void requestMapping(AnnotationTree mapping, Scope scope, List<String> basePaths, CompilationUnitTree unit, MethodTree method, int index, boolean validContext) {
        List<String> paths = List.of("");
        List<String> methods = null;
        boolean pathSeen = false;
        for (ExpressionTree arg : mapping.getArguments()) {
            if (!(arg instanceof AssignmentTree assignment)) { gaps.add("UNRESOLVED_ROUTE"); return; }
            String key = assignment.getVariable().toString();
            if (key.equals("method") && methods == null) methods = requestMethods(assignment.getExpression(), scope);
            else if ((key.equals("path") || key.equals("value")) && !pathSeen) {
                paths = literals(assignment.getExpression()); pathSeen = true;
            } else { gaps.add("UNRESOLVED_ROUTE"); return; }
        }
        if (!validContext || methods == null || paths == null || paths.isEmpty()) { gaps.add("UNRESOLVED_ROUTE"); return; }
        for (String suffix : paths) if (!suffix.matches("[A-Za-z0-9_/{}/.-]*") || suffix.length() > 256) { gaps.add("UNRESOLVED_ROUTE"); return; }
        for (String prefix : basePaths) for (String suffix : paths) for (String verb : methods) {
            String path = prefix.isEmpty() ? (suffix.isEmpty() ? "/" : suffix) : suffix.isEmpty() ? prefix : prefix + (prefix.endsWith("/") || suffix.startsWith("/") ? "" : "/") + suffix;
            if (!path.startsWith("/") || path.contains("//")) { gaps.add("UNRESOLVED_ROUTE"); return; }
            addFact(routes, row("httpMethod", verb, "path", path, "sourceIndex", index, "sourceLine", line(unit, method)));
            if (limitExceeded) return;
        }
    }

    private static Map<String, Object> row(Object... pairs) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) result.put((String) pairs[i], pairs[i + 1]);
        return result;
    }

    private long line(CompilationUnitTree u, Tree tree) {
        return u.getLineMap().getLineNumber(trees.getSourcePositions().getStartPosition(u, tree));
    }

    private boolean supportedAnnotation(AnnotationTree annotation, Scope scope) {
        String name = resolve(annotation.getAnnotationType(), scope);
        return name != null && Set.of(SPRING + "Configuration", SPRING + "Bean", WEB + "RestController", "org.springframework.stereotype.Controller", WEB + "RequestMapping", WEB + "GetMapping", WEB + "PostMapping", WEB + "PutMapping", WEB + "DeleteMapping", WEB + "PatchMapping").contains(name);
    }

    private boolean routeAnnotationsSafe(ModifiersTree modifiers, Scope scope, boolean classLevel) {
        for (AnnotationTree annotation : modifiers.getAnnotations()) {
            String name = resolve(annotation.getAnnotationType(), scope);
            if (name == null) return false;
            if (classLevel && Set.of(WEB + "RestController", "org.springframework.stereotype.Controller", WEB + "RequestMapping").contains(name)) continue;
            if (!classLevel && Set.of(WEB + "GetMapping", WEB + "PostMapping", WEB + "PutMapping", WEB + "DeleteMapping", WEB + "PatchMapping", WEB + "RequestMapping").contains(name)) continue;
            return false;
        }
        return true;
    }

    private void removeConflicts() {
        Set<String> names = new HashSet<>();
        Set<String> repeated = new HashSet<>();
        for (Map<String, Object> producer : producers) {
            List<String> all = new ArrayList<>();
            all.add((String) producer.get("beanName"));
            for (Object alias : (List<?>) producer.get("aliases")) all.add((String) alias);
            for (String name : all) if (!names.add(name)) repeated.add(name);
        }
        if (!repeated.isEmpty()) {
            producers.removeIf(p -> repeated.contains(p.get("beanName")) || ((List<?>) p.get("aliases")).stream().anyMatch(repeated::contains));
            gaps.add("CONFLICTING_BEAN_NAME");
        }
        if (limitExceeded) {
            types.clear(); producers.clear(); routes.clear(); gaps.add("FACT_LIMIT_EXCEEDED");
        }
    }

    private void process(CompilationUnitTree u, int index) {
        for (Tree decl : u.getTypeDecls()) {
            Scope s = scope(u);
            if (!(decl instanceof ClassTree c)) continue;
            if (!Set.of(Tree.Kind.CLASS, Tree.Kind.INTERFACE).contains(c.getKind())) { gaps.add("UNSUPPORTED_TYPE"); continue; }
            if (!c.getTypeParameters().isEmpty()) { gaps.add("GENERIC_TYPE_UNSUPPORTED"); continue; }
            String name = s.pkg.isEmpty() ? c.getSimpleName().toString() : s.pkg + "." + c.getSimpleName();
            if (duplicateTypes.contains(name)) { gaps.add("DUPLICATE_SOURCE_TYPE"); continue; }
            for (Tree member : c.getMembers()) {
                if (member instanceof ClassTree nested) s.shadows.add(nested.getSimpleName().toString());
                if (member instanceof VariableTree variable) s.shadows.add(variable.getName().toString());
            }
            List<String> supers = new ArrayList<>();
            boolean known = true;
            List<Tree> bases = new ArrayList<>();
            if (c.getExtendsClause() != null) bases.add(c.getExtendsClause());
            bases.addAll(c.getImplementsClause());
            for (Tree base : bases) {
                String resolved = resolve(base, s);
                if (resolved == null) known = false; else supers.add(resolved);
            }
            if (known) addFact(types, row("name", name, "directSupertypes", supers));
            else gaps.add("UNRESOLVED_SUPERTYPE");
            for (AnnotationTree annotation : c.getModifiers().getAnnotations()) if (!supportedAnnotation(annotation, s)) gaps.add("UNRESOLVED_ANNOTATION");
            boolean config = find(c.getModifiers(), s, SPRING + "Configuration") != null;
            boolean controller = find(c.getModifiers(), s, WEB + "RestController") != null || find(c.getModifiers(), s, "org.springframework.stereotype.Controller") != null;
            AnnotationTree classMapping = find(c.getModifiers(), s, WEB + "RequestMapping");
            List<String> basePaths = mappingPaths(classMapping);
            Map<String, Integer> methodCounts = new HashMap<>();
            for (Tree member : c.getMembers()) {
                if (member instanceof MethodTree method) methodCounts.merge(method.getName().toString(), 1, Integer::sum);
                if (member instanceof ClassTree) gaps.add("NESTED_TYPE_UNSUPPORTED");
            }
            for (Tree member : c.getMembers()) {
                if (!(member instanceof MethodTree method)) continue;
                for (AnnotationTree annotation : method.getModifiers().getAnnotations()) if (!supportedAnnotation(annotation, s)) gaps.add("UNRESOLVED_ANNOTATION");
                AnnotationTree bean = find(method.getModifiers(), s, SPRING + "Bean");
                if (bean != null) {
                    String declaredType = resolve(method.getReturnType(), s);
                    List<String> names = annotationNames(bean, method.getName().toString());
                    if (!config || declaredType == null || names == null || line(u, method) < 1 || methodCounts.get(method.getName().toString()) > 1 || !method.getTypeParameters().isEmpty()) { gaps.add("UNRESOLVED_BEAN"); continue; }
                    addFact(producers, row("beanName", names.get(0), "aliases", names.subList(1, names.size()), "declaredType", declaredType, "implementationType", null, "configurationClass", name, "factoryMethod", method.getName().toString(), "sourceIndex", index, "sourceLine", line(u, method)));
                    if (limitExceeded) return;
                }
                Map<String, String> methods = Map.of("GetMapping", "GET", "PostMapping", "POST", "PutMapping", "PUT", "DeleteMapping", "DELETE", "PatchMapping", "PATCH");
                int mappingCount = 0;
                for (String mappingName : methods.keySet()) if (find(method.getModifiers(), s, WEB + mappingName) != null) mappingCount++;
                AnnotationTree requestMapping = find(method.getModifiers(), s, WEB + "RequestMapping");
                if (requestMapping != null) mappingCount++;
                if (mappingCount > 1) { gaps.add("UNRESOLVED_ROUTE"); continue; }
                for (Map.Entry<String, String> entry : methods.entrySet()) {
                    AnnotationTree mapping = find(method.getModifiers(), s, WEB + entry.getKey());
                    if (mapping == null) continue;
                    List<String> paths = mappingPaths(mapping);
                    if (!controller || !bases.isEmpty() || basePaths == null || paths == null || line(u, method) < 1 || !routeAnnotationsSafe(c.getModifiers(), s, true) || !routeAnnotationsSafe(method.getModifiers(), s, false)) { gaps.add("UNRESOLVED_ROUTE"); continue; }
                    for (String prefix : basePaths) for (String suffix : paths) {
                        String path;
                        if (prefix.isEmpty()) path = suffix.isEmpty() ? "/" : suffix;
                        else if (suffix.isEmpty()) path = prefix;
                        else path = prefix + (prefix.endsWith("/") || suffix.startsWith("/") ? "" : "/") + suffix;
                        if (!path.startsWith("/") || path.contains("//")) { gaps.add("UNRESOLVED_ROUTE"); continue; }
                        addFact(routes, row("httpMethod", entry.getValue(), "path", path, "sourceIndex", index, "sourceLine", line(u, method)));
                        if (limitExceeded) return;
                    }
                }
                if (requestMapping != null) {
                    boolean valid = controller && bases.isEmpty() && basePaths != null && line(u, method) > 0 && routeAnnotationsSafe(c.getModifiers(), s, true) && routeAnnotationsSafe(method.getModifiers(), s, false);
                    requestMapping(requestMapping, s, basePaths, u, method, index, valid);
                    if (limitExceeded) return;
                }
            }
        }
    }

    private static String json(Object obj) {
        if (obj == null) return "null";
        if (obj instanceof String value) {
            StringBuilder b = new StringBuilder("\"");
            for (int i = 0; i < value.length(); i++) {
                char ch = value.charAt(i);
                if (ch == '"' || ch == '\\') b.append('\\').append(ch);
                else if (ch < 32) b.append(String.format("\\u%04x", (int) ch));
                else b.append(ch);
            }
            return b.append('"').toString();
        }
        if (obj instanceof Number || obj instanceof Boolean) return obj.toString();
        if (obj instanceof Map<?, ?> map) {
            List<String> entries = new ArrayList<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) entries.add(json(entry.getKey()) + ":" + json(entry.getValue()));
            return "{" + String.join(",", entries) + "}";
        }
        if (obj instanceof Collection<?> values) {
            List<String> entries = new ArrayList<>();
            for (Object value : values) entries.add(json(value));
            return "[" + String.join(",", entries) + "]";
        }
        throw new IllegalArgumentException("unsupported output");
    }

    public static void main(String[] args) {
        if (args.length == 0) { System.err.println("SOURCE_INPUT_REQUIRED"); System.exit(2); }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) { System.err.println("JDK_REQUIRED"); System.exit(2); }
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(new StringWriter(), manager, diagnostics, List.of("-proc:none"), null, manager.getJavaFileObjects(args));
            List<CompilationUnitTree> units = new ArrayList<>();
            task.parse().forEach(units::add);
            if (diagnostics.getDiagnostics().stream().anyMatch(d -> d.getKind() == Diagnostic.Kind.ERROR) || units.size() != args.length) {
                System.err.println("SOURCE_PARSE_FAILED"); System.exit(2);
            }
            SourceFacts facts = new SourceFacts();
            facts.trees = Trees.instance(task);
            for (CompilationUnitTree u : units) {
                String pkg = u.getPackageName() == null ? "" : u.getPackageName().toString();
                for (Tree tree : u.getTypeDecls()) if (tree instanceof ClassTree c) {
                    String name = pkg.isEmpty() ? c.getSimpleName().toString() : pkg + "." + c.getSimpleName();
                    if (!facts.declared.add(name)) facts.duplicateTypes.add(name);
                }
            }
            for (int i = 0; i < units.size() && !facts.limitExceeded; i++) facts.process(units.get(i), i);
            facts.removeConflicts();
            System.out.println(json(row("types", facts.types, "producers", facts.producers, "routes", facts.routes, "gaps", facts.gaps)));
        } catch (IOException e) {
            System.err.println("SOURCE_READ_FAILED"); System.exit(2);
        } catch (IllegalArgumentException e) {
            System.err.println("SOURCE_INPUT_INVALID"); System.exit(2);
        }
    }
}
