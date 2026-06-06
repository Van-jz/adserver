package com.leeyom.scaffold.factory;

import lombok.Data;

import java.math.BigDecimal;

/**
 * 广告信息
 */
@Data
public class Advert {

    /**
     * 广告id
     */
    private String id;

    /**
     * 广告名称
     */
    private String name;

    /**
     * 广告链接
     */
    private String linkUrl;

    private String adm;

    /**
     * 投放策略
     */
    private StrategyParam strategyParam;

    private BigDecimal bidPrice;


    private String cid;

    private String crid;


}
