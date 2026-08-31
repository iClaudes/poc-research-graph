FROM maven:3.9-eclipse-temurin-25 AS build
WORKDIR /build
COPY crawler/pom.xml crawler/pom.xml
COPY crawler/src crawler/src
RUN mvn -f crawler/pom.xml clean package -DskipTests

FROM eclipse-temurin:25-jre AS runtime
WORKDIR /app
COPY --from=build /build/crawler/target/crawler-0.1.0.jar /app/crawler.jar
RUN mkdir -p /app/downloads
ENTRYPOINT ["java", "-jar", "crawler.jar"]
