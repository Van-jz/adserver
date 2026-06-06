package com.leeyom.scaffold.factory;

import cn.hutool.core.util.RandomUtil;
import com.leeyom.scaffold.dto.req.User;
import com.leeyom.scaffold.enums.AdvChoiceStrategyEnum;
import lombok.Data;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 每1000次请求随机选一个广告参与竞价
 *
 * @author luoxun
 */
@Service("bid_one_per_1000")
@Data
public class AdvertChoiceBidOnePer1000 implements IAdvertChoice {

    private AtomicLong total = new AtomicLong();

    private Integer INTERVAL = 100000;

    @Override
    public AdvChoiceStrategyEnum getCode() {
        return AdvChoiceStrategyEnum.BID_ONE_PER_1000;
    }

    @Override
    public Advert choose(List<Advert> waitChooseAdvertList, UserBO userBO) {
        Long currentSequence = total.incrementAndGet();
        if (currentSequence % INTERVAL == 0) {
            if (!CollectionUtils.isEmpty(waitChooseAdvertList)) {
                //随机返回一个
                return waitChooseAdvertList.get(RandomUtil.randomInt(waitChooseAdvertList.size()));
            }
        }
        return null;
    }


}
