package com.leeyom.scaffold.factory;

import cn.hutool.core.util.RandomUtil;
import com.leeyom.scaffold.enums.AdvChoiceStrategyEnum;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;

/***
 *
 * 按广告挑选策略过滤广告，随机选取一条
 *
 * @author luoxun
 */
@Service("filter_by_criteria")
@Slf4j
public class AdvertChoiceFilterByCriteria implements IAdvertChoice {

    @Override
    public AdvChoiceStrategyEnum getCode() {
        return AdvChoiceStrategyEnum.FILTER_BY_CRITERIA;
    }

    @Override
    public Advert choose(List<Advert> waitChooseAdvertList, UserBO userBO) {
        List<Advert> chooseAdvertList = new ArrayList<>();
        for (Advert advert : waitChooseAdvertList) {
            StrategyParam strategyParam = advert.getStrategyParam();
            //依次过滤
            if (!CollectionUtils.isEmpty(strategyParam.getCountryList())) {
                if (!strategyParam.getCountryList().contains(userBO.getCountry())) {
                    log.info("国家不匹配");
                    continue;
                }
            }

            //依次过滤
            if (!CollectionUtils.isEmpty(strategyParam.getRegionList())) {
                if (!strategyParam.getRegionList().contains(userBO.getRegion())) {
                    log.info("区域不匹配");
                    continue;
                }
            }

            if (!CollectionUtils.isEmpty(strategyParam.getOsTypeList())) {
                if (!strategyParam.getOsTypeList().contains(userBO.getOsType())) {
                    log.info("终端类型不匹配");
                    continue;
                }
            }

            if (!CollectionUtils.isEmpty(strategyParam.getGenderList())) {
                if (!strategyParam.getGenderList().contains(userBO.getGender())) {
                    log.info("性别不匹配");
                    continue;
                }
            }
            if (strategyParam.getAgeMin() != null) {
                if (strategyParam.getAgeMin() > userBO.getAge()) {
                    log.info("年龄最小值不匹配");
                }
            }

            if (strategyParam.getAgeMax() != null) {
                if (strategyParam.getAgeMax() < userBO.getAge()) {
                    log.info("年龄最大值不匹配");
                }
            }
            //全部条件均符合
            chooseAdvertList.add(advert);
        }
        if (!CollectionUtils.isEmpty(chooseAdvertList)) {
            //随机返回一个
            return chooseAdvertList.get(RandomUtil.randomInt(chooseAdvertList.size()));
        }
        return null;
    }
}
