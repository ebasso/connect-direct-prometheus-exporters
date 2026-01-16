# Multi-stage build for IBM Connect:Direct Prometheus Exporter

# Stage 1: Build the application
FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /build

# Copy pom.xml and download dependencies (for layer caching)
COPY pom.xml .
# Copy the CDJAI.jar library and Install the CDJAI.jar to local Maven repository
COPY lib/CDJAI.jar /build/lib/CDJAI.jar
RUN mvn install:install-file -Dfile=/build/lib/CDJAI.jar -DgroupId=com.sterlingcommerce -DartifactId=cdjai -Dversion=1.0 -Dpackaging=jar
RUN mvn dependency:go-offline -B

# Copy source code and build
COPY CDExporter.java .
RUN mvn clean package -DskipTests

# Create default truststore
RUN keytool -genkeypair -alias dummy -keyalg RSA -keystore /build/truststore.jks -storetype JKS -storepass changeit -dname "CN=Dummy" -validity 3650

# Stage 2: Create runtime image
FROM eclipse-temurin:17-jre-alpine

# Create non-root user
RUN addgroup -g 1001 cdexporter && \
    adduser -D -u 1001 -G cdexporter cdexporter

WORKDIR /app

# Use a Java 17 base image for the runtime

# Copy JAR from builder stage
COPY --from=builder /build/target/cd-exporter.jar /app/cd-exporter.jar

# Copy default truststore
COPY --from=builder /build/truststore.jks /app/truststore.jks

# Change ownership
RUN chown -R cdexporter:cdexporter /app

# Switch to non-root user
USER cdexporter

# Expose Prometheus metrics port
EXPOSE 9402

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:9402/metrics || exit 1

# Set default environment variables (can be overridden)
ENV CD_NODE_IP=localhost
ENV CD_USER=admin
ENV CD_PASSWORD=password
ENV CD_PORT=1363
ENV CD_PROTOCOL=TCPIP
ENV HTTP_PORT=9402
ENV SCRAPE_INTERVAL=60
ENV TRUSTSTORE_PASSWORD=changeit

# Volume for truststore
# When running the container, you can mount the truststore file using:
# -v /host/path/to/truststore.jks:/app/truststore.jks 
VOLUME ["/app/truststore.jks"]

# Entrypoint
ENTRYPOINT ["java", "-Djavax.net.ssl.trustStore=/app/truststore.jks", "-Djavax.net.ssl.trustStorePassword=${TRUSTSTORE_PASSWORD}", "-jar", "/app/cd-exporter.jar"]

# Default CMD (can be overridden)
CMD ["--ipaddress=${CD_NODE_IP}", "--user=${CD_USER}", "--password=${CD_PASSWORD}", "--port=${CD_PORT}", "--protocol=${CD_PROTOCOL}", "--http-port=${HTTP_PORT}", "--scrape-interval=${SCRAPE_INTERVAL}"]