import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;

/** Start original application beans with operator-controlled disposable settings. */
public class ProjectDiagnosticsLauncher {
    public static void main(String[] args) {
        try {
            Properties properties = new Properties();
            try (InputStream input = Files.newInputStream(Path.of(args[1]))) {
                properties.load(input);
            }
            List<String> options = new ArrayList<>();
            for (String key : properties.stringPropertyNames()) {
                options.add("--" + key + "=" + properties.getProperty(key));
            }
            options.add("--logging.config=" + Path.of(args[1])
                .resolveSibling("logback-diagnostics.xml").toUri());
            SpringApplication app = new SpringApplication(Class.forName(args[0]));
            app.setApplicationStartup(new BufferingApplicationStartup(4096));
            ConfigurableApplicationContext context = app.run(options.toArray(String[]::new));
            String port = context.getEnvironment().getProperty("local.management.port");
            if (port == null) throw new IllegalStateException();
            String businessPort = context.getEnvironment().getProperty("local.server.port");
            if (businessPort == null) throw new IllegalStateException();
            System.out.println("PROJECT_DIAGNOSTICS_PORT_MODE="
                + (port.equals(businessPort) ? "shared" : "separate"));
            System.out.println("GUIDE_DIAGNOSTICS_READY=" + port
                + ";JAVA=" + Runtime.version().feature());
        } catch (Throwable failure) {
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
}
