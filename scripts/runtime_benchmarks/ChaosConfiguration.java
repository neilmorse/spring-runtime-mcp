package benchmark;

import de.codecentric.spring.boot.chaos.monkey.configuration.toggles.ChaosToggles;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import java.nio.file.Files;
import java.nio.file.Path;

@Configuration(proxyBeanMethods = false)
public class ChaosConfiguration {
    @Bean
    @Primary
    ChaosToggles benchmarkToggles() {
        return name -> Files.isRegularFile(Path.of("/work/runtime/health-down"));
    }

    @Bean
    BenchmarkDependency benchmarkDependency() {
        return new BenchmarkDependency();
    }

    @Bean
    BenchmarkHealthIndicator benchmarkHealthIndicator(BenchmarkDependency dependency) {
        return new BenchmarkHealthIndicator(dependency);
    }

    public static class BenchmarkDependency {
        public String status() {
            return "ready";
        }
    }

    public static class BenchmarkHealthIndicator implements HealthIndicator {
        private final BenchmarkDependency dependency;

        public BenchmarkHealthIndicator(BenchmarkDependency dependency) {
            this.dependency = dependency;
        }

        @Override
        public Health health() {
            return Health.up().withDetail("benchmarkState", dependency.status()).build();
        }
    }
}
