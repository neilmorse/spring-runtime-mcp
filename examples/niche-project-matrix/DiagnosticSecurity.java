import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;

/** Operator-owned management authentication for the disposable HertzBeat instance. */
@Configuration(proxyBeanMethods = false)
public class DiagnosticSecurity {
    private static boolean matches(String actual, String envName) {
        String expected = System.getenv(envName);
        return actual != null && expected != null
            && MessageDigest.isEqual(
                actual.getBytes(StandardCharsets.UTF_8),
                ("Bearer " + expected).getBytes(StandardCharsets.UTF_8));
    }

    @Bean
    FilterRegistrationBean<Filter> diagnosticActuatorFilter() {
        Filter filter = (request, response, chain) -> {
            HttpServletRequest req = (HttpServletRequest) request;
            HttpServletResponse res = (HttpServletResponse) response;
            String path = req.getRequestURI().substring(req.getContextPath().length());
            if (!path.equals("/actuator") && !path.startsWith("/actuator/")) {
                chain.doFilter(request, response);
                return;
            }
            if (!"GET".equals(req.getMethod()) && !"HEAD".equals(req.getMethod())) {
                res.setStatus(405);
                return;
            }
            String value = req.getHeader("Authorization");
            if (matches(value, "NICHE_DIAGNOSTICS_ADMIN")) {
                chain.doFilter(request, response);
                return;
            }
            res.setStatus(matches(value, "NICHE_DIAGNOSTICS_USER") ? 403 : 401);
        };
        FilterRegistrationBean<Filter> registration = new FilterRegistrationBean<>(filter);
        registration.addUrlPatterns("/actuator", "/actuator/*");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return registration;
    }
}