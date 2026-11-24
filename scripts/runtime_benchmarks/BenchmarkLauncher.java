package benchmark;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;

import java.util.Arrays;

public class BenchmarkLauncher {
    public static void main(String[] args) throws ClassNotFoundException {
        Class<?> applicationType = Class.forName(args[0]);
        SpringApplication application = args[1].equals("-")
                ? new SpringApplication(applicationType)
                : new SpringApplication(applicationType, Class.forName(args[1]));
        application.setApplicationStartup(new BufferingApplicationStartup(4096));
        application.run(Arrays.copyOfRange(args, 2, args.length));
    }
}
