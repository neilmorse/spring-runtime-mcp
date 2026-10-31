import java.io.InputStream;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;

/** Add operator-owned Actuator authentication and a startup buffer to native Fineract. */
public class FineractDiagnosticsLauncher {
    public static void main(String[] args) {
        String stage = "properties";
        try {
            Properties properties = new Properties();
            try (InputStream input = Files.newInputStream(Path.of(args[1]))) {
                properties.load(input);
            }
            List<String> options = new ArrayList<>();
            for (String key : properties.stringPropertyNames()) {
                options.add("--" + key + "=" + properties.getProperty(key));
            }
            options.add("--logging.config=" + Path.of(args[2]).toUri());
            stage = "constructApplication";
            Class<?> application = Class.forName(args[0]);
            SpringApplicationBuilder builder = new SpringApplicationBuilder(application);
            boolean reflected = false;
            try {
                Method configure = application.getDeclaredMethod(
                    "configureApplication", SpringApplicationBuilder.class);
                configure.setAccessible(true);
                builder = (SpringApplicationBuilder) configure.invoke(null, builder);
                reflected = true;
            } catch (ReflectiveOperationException | RuntimeException reflection) {
                builder.sources(
                    Class.forName("org.apache.fineract.infrastructure.core.boot.FineractWebApplicationConfiguration"),
                    Class.forName("org.apache.fineract.infrastructure.core.boot.FineractLiquibaseOnlyApplicationConfiguration"));
            }
            System.out.println("FINERACT_LAUNCHER_CONFIG="
                + (reflected ? "reflection" : "fallback"));
            builder.sources(Class.forName("DiagnosticSecurity"));
            builder.application().setApplicationStartup(new BufferingApplicationStartup(2048));
            stage = "runApplication";
            ConfigurableApplicationContext context = builder.run(options.toArray(String[]::new));
            stage = "observePorts";
            String port = context.getEnvironment().getProperty("local.management.port");
            String business = context.getEnvironment().getProperty("local.server.port");
            if (port == null) throw new MissingManagementPort();
            if (business == null) throw new MissingBusinessPort();
            System.out.println("PROJECT_DIAGNOSTICS_PORT_MODE="
                + (port.equals(business) ? "shared" : "separate"));
            System.out.println("GUIDE_DIAGNOSTICS_READY=" + port
                + ";JAVA=" + Runtime.version().feature());
        } catch (Throwable failure) {
            System.out.println("PROJECT_DIAGNOSTICS_BEAN=launcherStage_" + stage);
            Throwable cause = failure;
            for (int depth = 0; depth < 8 && cause != null; depth++) {
                System.out.println("PROJECT_DIAGNOSTICS_ERROR=" + cause.getClass().getName());
                if (cause instanceof org.springframework.beans.factory.BeanCreationException bean) {
                    System.out.println("PROJECT_DIAGNOSTICS_BEAN=" + bean.getBeanName());
                }
                if (cause instanceof org.springframework.beans.BeanInstantiationException bean) {
                    System.out.println("PROJECT_DIAGNOSTICS_CLASS=" + bean.getBeanClass().getName());
                }
                cause = cause.getCause();
            }
            System.exit(1);
        }
    }
    static class MissingManagementPort extends IllegalStateException {}
    static class MissingBusinessPort extends IllegalStateException {}
}