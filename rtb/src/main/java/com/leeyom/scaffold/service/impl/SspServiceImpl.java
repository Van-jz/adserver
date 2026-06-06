package com.leeyom.scaffold.service.impl;

import com.leeyom.scaffold.config.SysConfig;
import com.leeyom.scaffold.dto.req.BidRequest;
import com.leeyom.scaffold.dto.resp.BidResp;
import com.leeyom.scaffold.service.SspService;
import com.leeyom.scaffold.utils.JsonUtils;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.apache.commons.lang3.concurrent.BasicThreadFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
@EnableConfigurationProperties(SysConfig.class)
public class SspServiceImpl implements SspService {

    @Value("${bidUrl}")
    private String bidUrl;

    private static SysConfig sysConfig;

    private static ExecutorService executorService;

    private static OkHttpClient HTTP_CLIENT;

    @Autowired
    public SspServiceImpl(SysConfig sysConfig) {
        log.info("s", sysConfig);
        SspServiceImpl.sysConfig = sysConfig;
    }

    @PostConstruct
    public void init() {
        executorService = new ThreadPoolExecutor(
                sysConfig.getCoreThreadNum(), //核心线程数
                sysConfig.getMaxThreadNum(), //最大线程数
                sysConfig.getLiveTime(), //线程存活时间
                TimeUnit.SECONDS, //线程存活时间单位
                new LinkedBlockingQueue<>(sysConfig.getCapacity()), //线程队列
                new BasicThreadFactory.Builder().namingPattern(sysConfig.getThreadName() + "-%d").daemon(true).build()); //线程工厂
        HTTP_CLIENT = new OkHttpClient().newBuilder()
                .dispatcher(new Dispatcher(executorService)).build();
    }


    @Override
    public BidResp req(BidRequest bidRequest) {
        MediaType mediaType = MediaType.parse("application/json;charset=utf-8");
        RequestBody requestBody = RequestBody.create(mediaType, JsonUtils.Object2Json(bidRequest));
        Request req = new Request.Builder()
                .url(bidUrl)
                .post(requestBody)
                .build();
        Response response = null;
        String responseStr = "";
        try {
            response = HTTP_CLIENT.newCall(req).execute();
            responseStr = response.body().string();
        } catch (IOException e) {
            log.error("e={}", e);
            return null;
        }
        log.info("responseStr={}", responseStr);
        BidResp bidResp = JsonUtils.Json2Object(responseStr, BidResp.class);
        return bidResp;
    }
}
