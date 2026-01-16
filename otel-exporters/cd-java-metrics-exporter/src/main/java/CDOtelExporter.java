import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.LongUpDownCounter;
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.exporter.prometheus.PrometheusHttpServer;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.metrics.SdkMeterProvider;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.semconv.ResourceAttributes;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.Enumeration;
import java.util.concurrent.atomic.AtomicLong;

import com.sterlingcommerce.cd.sdk.Node;
import com.sterlingcommerce.cd.sdk.Version;
import com.sterlingcommerce.cd.sdk.MediatorEnum;
import com.sterlingcommerce.cd.sdk.CDProcess;
import com.sterlingcommerce.cd.sdk.ConnectionException;
import com.sterlingcommerce.cd.sdk.ConnectionInformation;
import com.sterlingcommerce.cd.sdk.LogonException;
import com.sterlingcommerce.cd.sdk.KQVException;
import com.sterlingcommerce.cd.sdk.MsgException;


/**
 * CDOtelExporter - OpenTelemetry Exporter for IBM Connect:Direct
 * Collects and exposes IBM Connect:Direct process metrics
 */
public class CDOtelExporter {

    private static final String NAMESPACE = "ibm_cd";
    private static final String CLASSNAME_STRING = "CDOtelExporter";
    private static final Logger LOGGER = Logger.getLogger(CLASSNAME_STRING);

    
    // Connect:Direct connection parameters
    private final String nodeIpAddress;
    private final String nodeApiPort;
    private final String nodeProtocol;   // examples: TLS12, TLS13, TCPIP
    private final String nodeUser;
    private final String nodePassword;
    
    // OpenTelemetry metrics
    private final Meter meter;
    private final LongUpDownCounter holdTotal;
    private final LongUpDownCounter waitTotal;
    private final LongUpDownCounter timerTotal;
    private final LongUpDownCounter execTotal;
    private final LongCounter scrapeErrors;
    
    // Track current values for up-down counters
    private final AtomicLong currentHold = new AtomicLong(0);
    private final AtomicLong currentWait = new AtomicLong(0);
    private final AtomicLong currentTimer = new AtomicLong(0);
    private final AtomicLong currentExec = new AtomicLong(0);
    
    public CDOtelExporter(String nodeIpAddress, String nodeApiPort, String nodeUser, String nodePassword, String nodeProtocol, OpenTelemetry openTelemetry) {
        this.nodeIpAddress = nodeIpAddress;
        this.nodeApiPort = nodeApiPort;
        this.nodeProtocol = nodeProtocol;
        this.nodeUser = nodeUser;
        this.nodePassword = nodePassword;
        
        // Get meter from OpenTelemetry
        this.meter = openTelemetry.getMeter("ibm-cd-exporter", "1.0.0");
        
        // Create UpDownCounters for process states
        this.holdTotal = meter
            .upDownCounterBuilder(NAMESPACE + "_processes_hold_total")
            .setDescription("Total processes in HOLD state")
            .setUnit("1")
            .build();
        
        this.waitTotal = meter
            .upDownCounterBuilder(NAMESPACE + "_processes_wait_total")
            .setDescription("Total processes in WAIT state")
            .setUnit("1")
            .build();
        
        this.timerTotal = meter
            .upDownCounterBuilder(NAMESPACE + "_processes_timer_total")
            .setDescription("Total processes in TIMER state")
            .setUnit("1")
            .build();
        
        this.execTotal = meter
            .upDownCounterBuilder(NAMESPACE + "_processes_exec_total")
            .setDescription("Total processes in EXEC state")
            .setUnit("1")
            .build();
        
        // Create Counter for errors
        this.scrapeErrors = meter
            .counterBuilder(NAMESPACE + "_scrape_errors_total")
            .setDescription("Total errors when collecting IBM Connect:Direct metrics")
            .setUnit("1")
            .build();
    }
    
    /**
     * Collects metrics from IBM Connect:Direct
     */
    public void collectMetrics() {
        try {
            LOGGER.info("Collecting IBM Connect:Direct metrics...");
            StringBuilder sb = getConnectDirectProcessData();

            if (sb == null) {
                LOGGER.warning("No process data retrieved from Connect:Direct");
                updateCounter(holdTotal, currentHold, 0);
                updateCounter(waitTotal, currentWait, 0);
                updateCounter(timerTotal, currentTimer, 0);
                updateCounter(execTotal, currentExec, 0);
                return;
            }
            
            String output = sb.toString();
            long holdCount = countOccurrences(output, "HOLD");
            long waitCount = countOccurrences(output, "WAIT");
            long timerCount = countOccurrences(output, "TIMER");
            long execCount = countOccurrences(output, "EXEC");

            // Update metrics with delta values
            updateCounter(holdTotal, currentHold, holdCount);
            updateCounter(waitTotal, currentWait, waitCount);
            updateCounter(timerTotal, currentTimer, timerCount);
            updateCounter(execTotal, currentExec, execCount);
            
            LOGGER.info(String.format("Metrics collected - HOLD: %d, WAIT: %d, TIMER: %d, EXEC: %d", 
                holdCount, waitCount, timerCount, execCount));

        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error collecting metrics", e);
            scrapeErrors.add(1);
        }
    }
    
    /**
     * Updates an UpDownCounter with the delta between new and old values
     */
    private void updateCounter(LongUpDownCounter counter, AtomicLong current, long newValue) {
        long oldValue = current.get();
        long delta = newValue - oldValue;
        
        if (delta != 0) {
            counter.add(delta);
            current.set(newValue);
        }
    }
    
    /**
     * MsgExceptions may be caused by multiple errors, each of which are
     * provided in the elements contained by the MsgException object.  The logic
     * below goes through each element and displays the error they contain.
     */
    private static void showErrorDetails(MsgException me) {
        Enumeration errorEnum = me.elements();
        while (errorEnum.hasMoreElements()) {
            System.out.println("  " + errorEnum.nextElement());
        }
    }

    /**
     * Gets process data from Connect:Direct
     * This method should be implemented to connect to IBM Connect:Direct
     */
    private StringBuilder getConnectDirectProcessData() throws Exception {
        com.sterlingcommerce.cd.sdk.Node cdNode = null;
        com.sterlingcommerce.cd.sdk.MediatorEnum selProcResults = null;
        com.sterlingcommerce.cd.sdk.ConnectionInformation ci = null;
        String portRange = "";
        String appName = "CDJAIExporter";
        int count = 0;
        StringBuilder sb = null;
        
        try {
            LOGGER.info("CDJAI Version: " + Version.buildvers);
            LOGGER.info("Connecting to Connect:Direct server");
            cdNode = new Node(this.nodeIpAddress + ";" + this.nodeApiPort, this.nodeUser, this.nodePassword.toCharArray(), this.nodeProtocol, appName, java.util.Locale.getDefault(), portRange, ci);

            /**
             * To see what is going back and forth to the Connect:Direct server turn traces on by uncommenting the line below.
             * Output is written to System.out.
             */
            //cdNode.getConnectionInfo().setTraceOn();
            String localNode = cdNode.getConnectionInfo().getNodeName();
            LOGGER.info("Signed on to Connect:Direct -- Node = " + localNode);

            // Issue a select process command
            selProcResults = cdNode.execute("select process");
            LOGGER.info("Select Process command executed");

            //System.out.println("==================== Results: Start ==================== ");
            while (selProcResults.hasMoreElements()) {
                if (sb == null) {
                    sb = new StringBuilder();
                }
                CDProcess processData = (CDProcess) selProcResults.getNextElement();
                //System.out.println(String.valueOf(count) + " ----->");
                //System.out.println(processData.toString());
                sb.append(processData.toString());
                count += 1;
            }
            LOGGER.info("Total processes = " + (count));
            //System.out.println("==================== Results: End ==================== ");

        } catch (ConnectionException ce) {
            showErrorDetails(ce);
        } catch (LogonException le) {
            le.printStackTrace();
        } catch (KQVException ke) {
            ke.printStackTrace();
        } catch (MsgException msge) {
            msge.printStackTrace();
            showErrorDetails(msge);
        } catch (Exception ex) {
            ex.printStackTrace();
        } finally {
            // Clean up resources
            try {
                if (selProcResults != null) {
                    selProcResults.empty();
                }
                selProcResults = null;
                if (cdNode != null) {
                    LOGGER.info("Disconnecting from Connect:Direct server");
                    cdNode.closeNode();
                }
            } catch (Exception ignored) {
                // Exception handling for cleanup
            }
        }
        
        return sb;
    }
    
    
    /**
     * Counts occurrences of a state in the output
     */
    private long countOccurrences(String output, String state) {
        long count = 0;
        int index = 0;
        
        while ((index = output.indexOf(state, index)) != -1) {
            count++;
            index += state.length();
        }
        
        return count;
    }
        
    
    /**
     * Parses command-line arguments into a map
     */
    private static Map<String, String> parseArguments(String[] args) {
        Map<String, String> arguments = new HashMap<>();
        
        for (String arg : args) {
            if (arg.startsWith("--")) {
                String[] parts = arg.substring(2).split("=", 2);
                if (parts.length == 2) {
                    arguments.put(parts[0], parts[1]);
                } else {
                    LOGGER.warning("Invalid argument format: " + arg);
                }
            }
        }
        
        return arguments;
    }

    /**
     * Main method to start the exporter
     */
    public static void main(String[] args) {
        try {            
            Map<String, String> arguments = parseArguments(args);
        
            // Validate required arguments
            if (!arguments.containsKey("ipaddress") || !arguments.containsKey("user") || !arguments.containsKey("password")) {
                System.err.println("Usage: java CDOtelExporter --ipaddress=<NODE> --user=<NODEUSER> --password=<NODEPASSWORD> [--port=<NODEAPIPORT>] [--protocol=<PROTOCOL>] [--http-port=<HTTP_PORT>] [--scrape-interval=<SCRAPE_INTERVAL>]");
                System.err.println("Example: java CDOtelExporter --ipaddress=192.168.1.13 --user=admin --password=password123 --port=1363 --protocol=TLS12 --http-port=9402 --scrape-interval=60");
                System.exit(1);
            }
            
            String nodeIpAddress = arguments.get("ipaddress");
            String nodeApiPort = arguments.get("port") != null ? arguments.get("port") : "1363";
            String nodeUser = arguments.get("user");
            String nodePassword = arguments.get("password");
            String nodeProtocol = arguments.get("protocol") != null ? arguments.get("protocol") : "TCPIP";
            int httpPort = arguments.containsKey("http-port") ? Integer.parseInt(arguments.get("http-port")) : 9402;
            int scrapeInterval = arguments.containsKey("scrape-interval") ? Integer.parseInt(arguments.get("scrape-interval")) : 60;
            
            LOGGER.info("Starting CDOtelExporter with configuration:  Node: " + nodeIpAddress + " Port: " + nodeApiPort + " User: " + nodeUser + " Protocol: " + nodeProtocol);
            LOGGER.info("Java truststore location: " + System.getProperty("javax.net.ssl.trustStore"));
            
            // Create OpenTelemetry SDK with Prometheus exporter
            Resource resource = Resource.getDefault().toBuilder()
                .put(ResourceAttributes.SERVICE_NAME, "ibm-cd-exporter")
                .put(ResourceAttributes.SERVICE_VERSION, "1.0.0")
                .build();
            
            PrometheusHttpServer prometheusServer = PrometheusHttpServer.builder()
                .setHost("0.0.0.0")
                .setPort(httpPort)
                .build();
            
            SdkMeterProvider meterProvider = SdkMeterProvider.builder()
                .setResource(resource)
                .registerMetricReader(prometheusServer)
                .build();
            
            OpenTelemetry openTelemetry = OpenTelemetrySdk.builder()
                .setMeterProvider(meterProvider)
                .build();
            
            // Add shutdown hook
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                LOGGER.info("Shutting down OpenTelemetry...");
                meterProvider.close();
            }));
            
            // Create exporter instance
            CDOtelExporter exporter = new CDOtelExporter(nodeIpAddress, nodeApiPort, nodeUser, nodePassword, nodeProtocol, openTelemetry);
            
            LOGGER.info("CDOtelExporter started on port " + httpPort);
            LOGGER.info("Metrics available at: http://localhost:" + httpPort + "/metrics");
            LOGGER.info("Scrape interval: " + scrapeInterval + " seconds");
            
            // Thread for periodic metric collection
            Thread collectorThread = new Thread(() -> {
                while (!Thread.currentThread().isInterrupted()) {
                    try {
                        exporter.collectMetrics();
                        Thread.sleep(scrapeInterval * 1000L);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            });
            collectorThread.setDaemon(false);
            collectorThread.start();
            
            LOGGER.info("Press Ctrl+C to stop");
            
            // Keep server running
            Thread.currentThread().join();

        } catch (IOException | InterruptedException e) {
            LOGGER.log(Level.SEVERE, "Error starting CDOtelExporter", e);
            System.exit(1);
        }
    }
}