package com.leeyom.scaffold.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "sys")
public class SysConfig {

    public Integer coreThreadNum;

    public Integer maxThreadNum;

    public Integer liveTime;

    public Integer capacity;

    public String threadName;

}
