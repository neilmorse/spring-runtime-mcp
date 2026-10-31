import java.util.ArrayList;
import java.util.Map;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.context.ApplicationContextInitializer;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.MapPropertySource;

/** The preceding management-only Bearer filter owns authentication on these paths. */
public class ShenyuManagement implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    public void initialize(ConfigurableApplicationContext context) {
        var paths = new ArrayList<>(Binder.get(context.getEnvironment())
            .bind("shenyu.shiro.white-list", Bindable.listOf(String.class)).get());
        paths.add("/actuator");
        paths.add("/actuator/**");
        context.getEnvironment().getPropertySources().addFirst(
            new MapPropertySource("operator-management-boundary", Map.of("shenyu.shiro.white-list", paths)));
    }
}
