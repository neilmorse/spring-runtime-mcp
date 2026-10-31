import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springdoc.core.configurer.SpringdocActuatorBeanFactoryConfigurer;
import org.springdoc.core.configurer.SpringdocBeanFactoryConfigurer;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.beans.factory.support.DefaultListableBeanFactory;
import org.springframework.beans.factory.support.RootBeanDefinition;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;

/** Real patched post-processors: absent, explicit and property-defined groups. */
public class SpringdocPatchedProbe {
    public static void main(String[] args) {
        var factory = new DefaultListableBeanFactory();
        var environment = new StandardEnvironment();
        // Use only synthetic properties, excluding host environment variables.
        environment.getPropertySources().remove("systemProperties");
        environment.getPropertySources().remove("systemEnvironment");
        var properties = new java.util.HashMap<String, Object>(Map.of(
            "management.endpoints.web.base-path", "/actuator",
            "springdoc.show-actuator", "true"));
        var created = new AtomicInteger();
        if (args[0].equals("explicit")) {
            var definition = new RootBeanDefinition(GroupedOpenApi.class);
            definition.setInstanceSupplier(() -> {
                created.incrementAndGet();
                throw new AssertionError();
            });
            factory.registerBeanDefinition("explicitGroup", definition);
        }
        if (args[0].equals("property")) {
            properties.put("springdoc.group-configs[0].group", "synthetic");
            properties.put("springdoc.group-configs[0].paths-to-match[0]", "/api/**");
        }
        environment.getPropertySources().addFirst(new MapPropertySource("synthetic", properties));
        var general = new SpringdocBeanFactoryConfigurer();
        general.setEnvironment(environment);
        general.postProcessBeanFactory(factory);
        // Exercise both the new factory path and binary-compatible constructor.
        var configurer = args[0].equals("null-list")
            ? new SpringdocActuatorBeanFactoryConfigurer(null)
            : args[0].equals("explicit")
            ? new SpringdocActuatorBeanFactoryConfigurer(List.of())
            : new SpringdocActuatorBeanFactoryConfigurer();
        configurer.setEnvironment(environment);
        configurer.postProcessBeanFactory(factory);
        boolean expectedDefault = args[0].equals("absent") || args[0].equals("null-list");
        if (factory.containsSingleton("springdocDefault") != expectedDefault
                || !factory.containsSingleton("x-actuator") || created.get() != 0
                || (args[0].equals("property") && !factory.containsSingleton("synthetic"))) {
            throw new AssertionError();
        }
        System.out.println("PATCH_PROBE_OK=" + args[0]);
    }
}
