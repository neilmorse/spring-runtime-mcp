package benchmark;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Configuration(proxyBeanMethods = false)
public class DriftConfiguration {
    @Bean
    @ConditionalOnProperty(name = "benchmark.route.enabled", havingValue = "true")
    BenchmarkController benchmarkController() {
        return new BenchmarkController();
    }

    @Bean
    String benchmarkSlowBean() throws InterruptedException {
        Thread.sleep(300);
        return "ready";
    }
}

@RestController
class BenchmarkController {
    @GetMapping("/benchmark/registered")
    String registered() {
        return "ready";
    }
}
