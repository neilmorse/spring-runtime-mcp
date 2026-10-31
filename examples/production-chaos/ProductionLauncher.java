import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;

/** Run original application configuration; emit fixed readiness/error facts only. */
public class ProductionLauncher {
    public static void main(String[] args) {
        String stage = "properties";
        try {
            Properties properties = new Properties();
            try (InputStream input = Files.newInputStream(Path.of(args[1]))) {
                properties.load(input);
            }
            List<String> options = new ArrayList<>();
            for (String key : properties.stringPropertyNames())
                options.add("--" + key + "=" + properties.getProperty(key));
            options.add("--logging.config=" + Path.of(args[2]).toUri());
            List<Class<?>> sources = new ArrayList<>();
            sources.add(Class.forName(args[0]));
            sources.add(DiagnosticSecurity.class);
            sources.add(ChaosConfiguration.class);
            stage = "nativeStartup";
            SpringApplication app = new SpringApplication(sources.toArray(Class<?>[]::new));
            for (int i = 3; i < args.length; i++) {
                app.addInitializers((org.springframework.context.ApplicationContextInitializer<?>)
                    Class.forName(args[i]).getDeclaredConstructor().newInstance());
            }
            app.setApplicationStartup(new BufferingApplicationStartup(8192));
            ConfigurableApplicationContext context = app.run(options.toArray(String[]::new));
            if (context.getEnvironment().getProperty("diagnostics.install", Boolean.class, false)) {
                stage = "nativeDatabaseInstall";
                Class<?> type = Class.forName("org.thingsboard.server.install.ThingsboardInstallService");
                type.getMethod("performInstall").invoke(context.getBean(type));
                context.close();
                System.out.println("GUIDE_DIAGNOSTICS_READY=8080;JAVA=" + Runtime.version().feature());
                System.exit(0);
            }
            stage = "ports";
            String port = context.getEnvironment().getProperty("local.management.port");
            String business = context.getEnvironment().getProperty("local.server.port");
            if (port == null || business == null) throw new IllegalStateException();
            System.out.println("PROJECT_DIAGNOSTICS_PORT_MODE=" + (port.equals(business) ? "shared" : "separate"));
            System.out.println("GUIDE_DIAGNOSTICS_READY=" + port + ";JAVA=" + Runtime.version().feature());
        } catch (Throwable failure) {
            System.out.println("PROJECT_DIAGNOSTICS_BEAN=launcherStage_" + stage);
            Throwable cause = failure;
            for (int depth = 0; depth < 12 && cause != null; depth++) {
                System.out.println("PROJECT_DIAGNOSTICS_ERROR=" + cause.getClass().getName());
                if (cause instanceof IllegalStateException && cause.getMessage() != null) {
                    String message = cause.getMessage();
                    if (message.contains("Logback") || message.contains("logback"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=logbackConfiguration");
                    if (message.contains("Error processing condition"))
                        System.out.println("PROJECT_DIAGNOSTICS_BEAN=conditionProcessing");
                }
                if (cause instanceof org.springframework.beans.factory.BeanCreationException bean)
                    System.out.println("PROJECT_DIAGNOSTICS_BEAN=" + bean.getBeanName());
                if (cause instanceof org.springframework.beans.factory.support.BeanDefinitionOverrideException bean)
                    System.out.println("PROJECT_DIAGNOSTICS_BEAN=" + bean.getBeanName());
                if (cause instanceof org.springframework.beans.BeanInstantiationException bean)
                    System.out.println("PROJECT_DIAGNOSTICS_CLASS=" + bean.getBeanClass().getName());
                cause = cause.getCause();
            }
            System.exit(1);
        }
    }
}
