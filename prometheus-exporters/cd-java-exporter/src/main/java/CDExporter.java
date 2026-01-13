import io.prometheus.client.Counter;
import io.prometheus.client.Gauge;
import io.prometheus.client.exporter.HTTPServer;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.Enumeration;

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
 * CDExporter - Prometheus Exporter for IBM Connect:Direct
 * Collects and exposes IBM Connect:Direct process metrics
 */
public class CDExporter {

    private static final String NAMESPACE = "ibm_cd";
    private static final String CLASSNAME_STRING = "CDExporter";
    private static final Logger LOGGER = Logger.getLogger(CLASSNAME_STRING);

    
    // Connect:Direct connection parameters
    private final String nodeIpAddress;
    private final String nodeApiPort;
    private final String nodeProtocol;   // examples: TLS12, TLS13, TCPIP
    private final String nodeUser;
    private final String nodePassword;
    
    // Gauge metrics for process states
    private final Gauge holdTotal;
    private final Gauge waitTotal;
    private final Gauge timerTotal;
    private final Gauge execTotal;
    
    // Error counter
    private final Counter scrapeErrors;
    
    public CDExporter(String nodeIpAddress, String nodeApiPort, String nodeUser, String nodePassword, String nodeProtocol) {
        this.nodeIpAddress = nodeIpAddress;
        this.nodeApiPort = nodeApiPort;
        this.nodeProtocol = nodeProtocol;
        this.nodeUser = nodeUser;
        this.nodePassword = nodePassword;
        
        // Total processes in HOLD state
        this.holdTotal = Gauge.build()
            .name(NAMESPACE + "_processes_hold_total")
            .help("Total processes in HOLD state")
            .register();
        
        // Total processes in WAIT state
        this.waitTotal = Gauge.build()
            .name(NAMESPACE + "_processes_wait_total")
            .help("Total processes in WAIT state")
            .register();
        
        // Total processes in TIMER state
        this.timerTotal = Gauge.build()
            .name(NAMESPACE + "_processes_timer_total")
            .help("Total processes in TIMER state")
            .register();
        
        // Total processes in EXEC state
        this.execTotal = Gauge.build()
            .name(NAMESPACE + "_processes_exec_total")
            .help("Total processes in EXEC state")
            .register();
                
        // Error counter for metric collection
        this.scrapeErrors = Counter.build()
            .name(NAMESPACE + "_scrape_errors_total")
            .help("Total errors when collecting IBM Connect:Direct metrics")
            .register();
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
                holdTotal.set(0);
                waitTotal.set(0);
                timerTotal.set(0);
                execTotal.set(0);
                return;
            }
            
            String output = sb.toString();
            Integer holdCount = countOccurrences(output, "HOLD");
            Integer waitCount = countOccurrences(output, "WAIT");
            Integer timerCount = countOccurrences(output, "TIMER");
            Integer execCount = countOccurrences(output, "EXEC");

            // Update metrics
            holdTotal.set(holdCount);
            waitTotal.set(waitCount);
            timerTotal.set(timerCount);
            execTotal.set(execCount);
            LOGGER.info(String.format("Metrics collected - HOLD: %d, WAIT: %d, TIMER: %d, EXEC: %d", holdCount, waitCount, timerCount, execCount));

        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error collecting metrics", e);
            scrapeErrors.inc();
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
    private int countOccurrences(String output, String state) {
        int count = 0;
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
                System.err.println("Usage: java CDExporter --ipaddress=<NODE> --user=<NODEUSER> --password=<NODEPASSWORD> [--port=<NODEAPIPORT>] [--protocol=<PROTOCOL>] [--http-port=<HTTP_PORT>] [--scrape-interval=<SCRAPE_INTERVAL>]");
                System.err.println("Example: java CDExporter --ipaddress=192.168.1.13 --user=admin --password=password123 --port=1363 --protocol=TLS12 --http-port=9402 --scrape-interval=60");
                System.exit(1);
            }
            
            String nodeIpAddress = arguments.get("ipaddress");
            String nodeApiPort = arguments.get("port") != null ? arguments.get("port") : "1363";
            String nodeUser = arguments.get("user");
            String nodePassword = arguments.get("password");
            String nodeProtocol = arguments.get("protocol") != null ? arguments.get("protocol") : "TCPIP";
            int httpPort = arguments.containsKey("http-port") ? Integer.parseInt(arguments.get("http-port")) : 9402;
            int scrapeInterval = arguments.containsKey("scrape-interval") ? Integer.parseInt(arguments.get("scrape-interval")) : 60;
            
            LOGGER.info("Starting CDExporter with configuration:  Node: " + nodeIpAddress + " Port: " + nodeApiPort + " User: " + nodeUser + " Protocol: " + nodeProtocol);

            LOGGER.info("Java truststore location: " + System.getProperty("javax.net.ssl.trustStore"));
            
            // Create exporter instance
            CDExporter exporter = new CDExporter(nodeIpAddress, nodeApiPort, nodeUser, nodePassword, nodeProtocol);
            
            // Start HTTP server
            HTTPServer server = new HTTPServer(httpPort);
            
            LOGGER.info("CDExporter started on port " + httpPort);
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
            LOGGER.log(Level.SEVERE, "Error starting CDExporter", e);
            System.exit(1);
        }
    }
}