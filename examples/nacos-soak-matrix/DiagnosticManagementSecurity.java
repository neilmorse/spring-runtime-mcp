package com.alibaba.nacos.diagnostics;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import javax.servlet.Filter;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.boot.actuate.autoconfigure.web.ManagementContextConfiguration;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.core.Ordered;

/** Operator-owned authentication for the disposable Nacos management origin. */
@ManagementContextConfiguration(proxyBeanMethods = false)
public class DiagnosticManagementSecurity {
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
            if (matches(value, "NACOS_DIAGNOSTICS_ADMIN")) {
                chain.doFilter(request, response);
                return;
            }
            res.setStatus(matches(value, "NACOS_DIAGNOSTICS_USER") ? 403 : 401);
        };
        FilterRegistrationBean<Filter> registration = new FilterRegistrationBean<>(filter);
        registration.addUrlPatterns("/actuator", "/actuator/*");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return registration;
    }
}