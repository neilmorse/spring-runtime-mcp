import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;

/** Add only operator-owned Actuator authentication to the native application. */
public class LargeProjectLauncher {
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
            SpringApplication app = new SpringApplication(
                Class.forName(args[0]), Class.forName("DiagnosticSecurity"));
            app.setApplicationStartup(new BufferingApplicationStartup(8192));
            stage = "runApplication";
            ConfigurableApplicationContext context = app.run(options.toArray(String[]::new));
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
                if (cause instanceof IllegalStateException) {
                    String message = cause.getMessage();
                    if (message != null && message.startsWith("Error processing condition"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=conditionProcessing");
                    if (message != null && message.startsWith("Logback configuration error"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=logbackConfiguration");
                    if (message != null && message.startsWith("Unable to load config data"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=configDataLoading");
                    if (message != null && message.contains("Management-specific server address"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=managementAddressRequiresSeparatePort");
                    if (message != null && message.contains("WebSecurityConfigurerAdapter")
                        && message.contains("SecurityFilterChain"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=legacySecurityConfigurerConflict");
                }
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
