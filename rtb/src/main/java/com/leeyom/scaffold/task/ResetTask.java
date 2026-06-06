package com.leeyom.scaffold.task;

import com.leeyom.scaffold.api.BidProdController;
import com.leeyom.scaffold.factory.AdvertChoiceBidOnePer1000;
import com.leeyom.scaffold.utils.DateUtils;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.util.*;

@Service
@Slf4j
@Data
public class ResetTask {

    @Resource
    private AdvertChoiceBidOnePer1000 advertChoiceBidOnePer1000;

    private Integer INIT_INTERVAL = 100;

    @Scheduled(cron = "0 0 1 * * ? ", zone = "Asia/Shanghai") //每天1点（北京时间）执行一次
    public void resetInterval() {
        log.error("重置出价频率：");
        advertChoiceBidOnePer1000.setINTERVAL(INIT_INTERVAL);
        for (Map.Entry<Integer, BigDecimal> entry : BidProdController.wonPriceMap.entrySet()) {
            log.error("entry:{},priceTotal:{}", entry.getKey(), entry.getValue().toPlainString());
        }
    }


}
