package com.leeyom.scaffold;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 启动类
 *
 * @author leeyom
 */
@SpringBootApplication
@EnableAsync
@EnableConfigurationProperties
@EnableScheduling
public class SpringbootScaffoldApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringbootScaffoldApplication.class, args);
    }

}
