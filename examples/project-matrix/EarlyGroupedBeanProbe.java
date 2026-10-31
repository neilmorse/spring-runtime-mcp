import java.util.List;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.beans.factory.config.BeanFactoryPostProcessor;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Synthetic Spring lifecycle experiment. No server, target or credentials. */
public class EarlyGroupedBeanProbe {
    public static class Properties {}

    @Configuration(proxyBeanMethods = false)
    public static class PropertiesConfiguration {
        @Bean Properties properties() { return new Properties(); }
    }

    @Configuration
    public static class Groups {
        public Groups(Properties properties) {}
        @Bean GroupedOpenApi api() {
            return GroupedOpenApi.builder().group("synthetic").pathsToMatch("/api/**").build();
        }
    }

    @Configuration(proxyBeanMethods = false)
    public static class EagerConsumer {
        @Bean static BeanFactoryPostProcessor processor(List<GroupedOpenApi> groups) {
            return factory -> {};
        }
    }

    @Configuration(proxyBeanMethods = false)
    public static class DefinitionsOnlyConsumer {
        @Bean static BeanFactoryPostProcessor processor() {
            return factory -> {
                if (factory.getBeanNamesForType(GroupedOpenApi.class, true, false).length != 1) {
                    throw new IllegalStateException();
                }
            };
        }
    }

    public static void main(String[] args) {
        try (var context = new AnnotationConfigApplicationContext()) {
            context.register(PropertiesConfiguration.class, Groups.class);
            if (args[0].equals("eager")) context.register(EagerConsumer.class);
            if (args[0].equals("definitions-only")) context.register(DefinitionsOnlyConsumer.class);
            context.refresh();
            System.out.println("PROBE_READY=" + context.getBeansOfType(GroupedOpenApi.class).size());
        } catch (Throwable failure) {
            Throwable cause = failure;
            for (int depth = 0; depth < 8 && cause != null; depth++) {
                System.out.println("PROBE_ERROR=" + cause.getClass().getName());
                cause = cause.getCause();
            }
            System.exit(1);
        }
    }
}
