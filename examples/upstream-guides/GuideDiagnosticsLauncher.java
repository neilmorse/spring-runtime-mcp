import java.util.HashMap;
import java.util.Map;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Configuration;

/** Disposable launcher: preserve guide beans without running its demo HTTP client. */
public class GuideDiagnosticsLauncher {
    @ConfigurationProperties(prefix = "guide")
    public static class GuideProperties {
        private String mode;
        private String apiToken;

        public String getMode() { return mode; }
        public void setMode(String mode) { this.mode = mode; }
        public String getApiToken() { return apiToken; }
        public void setApiToken(String apiToken) { this.apiToken = apiToken; }
    }

    @Configuration(proxyBeanMethods = false)
    @EnableConfigurationProperties(GuideProperties.class)
    public static class DiagnosticsConfiguration {}

    public static void main(String[] args) {
        try {
            SpringApplication app = new SpringApplication(
                Class.forName(args[0]), DiagnosticsConfiguration.class);
            app.setApplicationStartup(new BufferingApplicationStartup(2048));
            Map<String, Object> defaults = new HashMap<>();
            defaults.put("server.address", "127.0.0.1");
            defaults.put("server.port", "0");
            defaults.put("management.server.address", "127.0.0.1");
            defaults.put("management.server.port", "0");
            defaults.put("management.endpoints.web.exposure.include",
                "health,beans,conditions,mappings,startup,env,configprops");
            defaults.put("management.endpoint.health.show-details", "never");
            defaults.put("management.endpoint.env.show-values", "always");
            defaults.put("management.endpoint.configprops.show-values", "always");
            defaults.put("spring.application.name", "guide-diagnostics");
            defaults.put("spring.main.banner-mode", "off");
            defaults.put("logging.level.root", "ERROR");
            defaults.put("guide.mode", "diagnostics");
            defaults.put("guide.api-token", System.getenv("GUIDE_SYNTHETIC_SECRET"));
            app.setDefaultProperties(defaults);
            ConfigurableApplicationContext context = app.run();
            String port = context.getEnvironment().getProperty("local.management.port");
            if (port == null) throw new IllegalStateException();
            System.out.println("GUIDE_DIAGNOSTICS_READY=" + port
                + ";JAVA=" + Runtime.version().feature());
        } catch (Throwable failure) {
            System.out.println("GUIDE_DIAGNOSTICS_FAILED");
            System.exit(1);
        }
    }
}
