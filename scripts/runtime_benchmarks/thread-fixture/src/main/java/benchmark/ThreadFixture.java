package benchmark;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.SpringBootVersion;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ThreadFixture {
    public static void main(String[] args) throws InterruptedException, IOException {
        var environment = SpringApplication.run(ThreadFixture.class, args).getEnvironment();
        String mode = environment.getRequiredProperty("benchmark.thread.mode");
        Path directory = Path.of("/work/runtime", mode);
        awaitStart(directory.resolve("start"));
        Thread[] workers = switch (mode) {
            case "blocked" -> blocked();
            case "deadlock" -> deadlock();
            case "timed" -> timed();
            default -> throw new IllegalArgumentException("unknown trial mode");
        };
        if (mode.equals("deadlock")) {
            // Force a second result so acceptance can verify cursor reuse.
            blocked();
        }
        recordOracle(mode, directory, workers);
        if (mode.equals("timed")) {
            for (Thread worker : workers) {
                worker.join(20_000);
                if (worker.isAlive()) {
                    throw new IllegalStateException("timed lock worker did not recover");
                }
            }
            Files.createFile(directory.resolve("recovered"));
        }
    }

    private static void awaitStart(Path marker) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(45);
        while (!Files.exists(marker)) {
            if (System.nanoTime() >= deadline) {
                throw new IllegalStateException("fixture did not receive start signal");
            }
            Thread.sleep(20);
        }
    }

    private record Oracle(String bootVersion, long waiterId, long ownerId,
        String waiterState, String ownerState, long[] deadlockedIds) {}

    private static void recordOracle(String mode, Path directory, Thread[] workers)
            throws InterruptedException, IOException {
        ThreadMXBean jvm = ManagementFactory.getThreadMXBean();
        long first = workers[0].threadId();
        long second = workers[1].threadId();
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while (System.nanoTime() < deadline) {
            ThreadInfo a = jvm.getThreadInfo(first);
            ThreadInfo b = jvm.getThreadInfo(second);
            if (a != null && b != null && a.getLockOwnerId() == second
                && (mode.equals("blocked") || b.getLockOwnerId() == first)) {
                long[] deadlocked = jvm.findDeadlockedThreads();
                var oracle = new Oracle(SpringBootVersion.getVersion(), first, second,
                    a.getThreadState().name(), b.getThreadState().name(),
                    deadlocked == null ? new long[0] : deadlocked);
                Path draft = directory.resolve("oracle.tmp");
                new ObjectMapper().writeValue(draft.toFile(), oracle);
                Files.move(draft, directory.resolve("oracle.json"), StandardCopyOption.ATOMIC_MOVE);
                return;
            }
            Thread.sleep(20);
        }
        throw new IllegalStateException("fixture failed to reach expected thread states");
    }

    private static Thread[] blocked() throws InterruptedException {
        Object lock = new Object();
        CountDownLatch held = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        Thread owner = start("private-fixture-owner", () -> {
            synchronized (lock) {
                held.countDown();
                await(release);
            }
        });
        held.await();
        Thread waiter = start("private-fixture-waiter", () -> {
            synchronized (lock) {
                throw new AssertionError("lock acquired unexpectedly");
            }
        });
        return new Thread[] {waiter, owner};
    }

    private static Thread[] deadlock() {
        Object left = new Object();
        Object right = new Object();
        CountDownLatch held = new CountDownLatch(2);
        return new Thread[] {
            start("private-fixture-left", () -> monitorWait(left, right, held)),
            start("private-fixture-right", () -> monitorWait(right, left, held)),
        };
    }

    private static void monitorWait(Object first, Object second, CountDownLatch held) {
        synchronized (first) {
            held.countDown();
            await(held);
            synchronized (second) {
                throw new AssertionError("lock acquired unexpectedly");
            }
        }
    }

    private static Thread[] timed() {
        ReentrantLock left = new ReentrantLock();
        ReentrantLock right = new ReentrantLock();
        CountDownLatch held = new CountDownLatch(2);
        return new Thread[] {
            start("private-fixture-timed-left", () -> timedWait(left, right, held)),
            start("private-fixture-timed-right", () -> timedWait(right, left, held)),
        };
    }

    private static void timedWait(ReentrantLock first, ReentrantLock second, CountDownLatch held) {
        first.lock();
        try {
            held.countDown();
            await(held);
            if (second.tryLock(12, TimeUnit.SECONDS)) {
                second.unlock();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            first.unlock();
        }
    }

    private static Thread start(String name, Runnable worker) {
        return Thread.ofPlatform().name(name).daemon().start(worker);
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }
}
