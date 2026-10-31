import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.Principal;
import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Enforce management-only Bearer authorization before native application filters. */
@Configuration(proxyBeanMethods = false)
public class DiagnosticSecurity {
    private static boolean matches(String actual, String env) {
        String expected = System.getenv(env);
        return actual != null && expected != null && MessageDigest.isEqual(
            actual.getBytes(StandardCharsets.UTF_8),
            ("Bearer " + expected).getBytes(StandardCharsets.UTF_8));
    }

    @Bean
    FilterRegistrationBean<Filter> diagnosticActuatorSecurity() {
        Filter bearer = new Filter() {
            public void init(jakarta.servlet.FilterConfig config) { }
            public void destroy() { }
            public void doFilter(jakarta.servlet.ServletRequest request,
                jakarta.servlet.ServletResponse response, jakarta.servlet.FilterChain chain)
                throws java.io.IOException, jakarta.servlet.ServletException {
            HttpServletRequest req = (HttpServletRequest) request;
            HttpServletResponse res = (HttpServletResponse) response;
            if (!req.getMethod().equals("GET") && !req.getMethod().equals("HEAD")) {
                res.setStatus(405);
                return;
            }
            String value = req.getHeader("Authorization");
            boolean admin = matches(value, "LARGE_DIAGNOSTICS_ADMIN");
            if (!admin && !matches(value, "LARGE_DIAGNOSTICS_USER")) {
                res.setStatus(401);
                return;
            }
            if (!admin) {
                res.setStatus(403);
                return;
            }
            chain.doFilter(new HttpServletRequestWrapper(req) {
                public Principal getUserPrincipal() { return () -> "diagnostics"; }
                public String getRemoteUser() { return "diagnostics"; }
                public boolean isUserInRole(String role) {
                    return role.equals("DIAGNOSTICS") || role.equals("ROLE_DIAGNOSTICS");
                }
            }, response);
            }
        };
        FilterRegistrationBean<Filter> registration = new FilterRegistrationBean<>(bearer);
        registration.setOrder(Integer.MIN_VALUE);
        registration.addUrlPatterns("/actuator", "/actuator/*");
        return registration;
    }
}
