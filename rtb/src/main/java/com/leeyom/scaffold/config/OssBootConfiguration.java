package com.leeyom.scaffold.config;

import com.leeyom.scaffold.help.OssBootHelper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OssBootConfiguration {

    @Value("${app.oss.endpoint}")
    private String endpoint;
    @Value("${app.oss.accessKey}")
    private String accessKeyId;
    @Value("${app.oss.secretKey}")
    private String accessKeySecret;
    @Value("${app.oss.bucketName}")
    private String bucketName;
    @Value("${app.oss.staticDomain}")
    private String staticDomain;


    @Bean
    public void initOssBootConfiguration() {
        OssBootHelper.setEndPoint(endpoint);
        OssBootHelper.setAccessKeyId(accessKeyId);
        OssBootHelper.setAccessKeySecret(accessKeySecret);
        OssBootHelper.setBucketName(bucketName);
        OssBootHelper.setStaticDomain(staticDomain);
    }
}