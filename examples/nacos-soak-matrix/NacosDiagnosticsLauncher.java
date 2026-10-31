package com.alibaba.nacos.diagnostics;

import com.alibaba.nacos.Nacos;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;

/** Operator launcher: adds a bounded startup buffer without changing Nacos sources. */
public class NacosDiagnosticsLauncher {
    public static void main(String[] args) {
        String stage = "properties";
        try {
            Properties properties = new Properties();
            try (InputStream input = Files.newInputStream(Path.of(args[0]))) {
                properties.load(input);
            }
            List<String> options = new ArrayList<>();
            for (String key : properties.stringPropertyNames()) {
                options.add("--" + key + "=" + properties.getProperty(key));
            }
            String databasePassword = System.getenv("NACOS_DB_PASSWORD");
            if (databasePassword != null && !databasePassword.isBlank()) {
                options.add("--db.password.0=" + databasePassword);
            }
            options.add("--logging.config=" + Path.of(args[1]).toUri());
            stage = "runApplication";
            SpringApplication app = new SpringApplication(
                Nacos.class, DiagnosticManagementSecurity.class);
            app.setApplicationStartup(new BufferingApplicationStartup(8192));
            ConfigurableApplicationContext context = app.run(options.toArray(String[]::new));
            String management = context.getEnvironment().getProperty("local.management.port");
            String business = context.getEnvironment().getProperty("local.server.port");
            if (management == null || business == null) {
                throw new IllegalStateException("missing local ports");
            }
            System.out.println("NACOS_DIAGNOSTICS_READY=" + management
                + ";BUSINESS=" + business + ";JAVA=" + Runtime.version().feature());
            System.out.println("PROJECT_DIAGNOSTICS_PORT_MODE=separate");
            System.out.println("GUIDE_DIAGNOSTICS_READY=" + management
                + ";JAVA=" + Runtime.version().feature());
        } catch (Throwable failure) {
            System.out.println("NACOS_DIAGNOSTICS_STAGE=" + stage);
            Throwable cause = failure;
            for (int depth = 0; depth < 8 && cause != null; depth++) {
                System.out.println("PROJECT_DIAGNOSTICS_ERROR=" + cause.getClass().getName());
                cause = cause.getCause();
            }
            System.exit(1);
        }
    }
}