package com.leeyom.scaffold.service.condition;

import lombok.Data;
import lombok.ToString;
import java.io.Serializable;

import java.math.BigDecimal;
import java.util.Date;

/**
 * <p>
 * 广告消耗日报 查询条件
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@ToString
public class QueryAdPerformanceDayReportCondition extends BaseCondition implements Serializable{
    private static final long serialVersionUID = 1L;

    /**
     * 日期
     */
    private Date date;

    /**
     * 出价次数
     */
    private Integer bidTimes;

    /**
     * 曝光次数
     */
    private Integer impressions;

    /**
     * 消耗
     */
    private BigDecimal spend;

    /**
     * 平均CPM
     */
    private BigDecimal avgCpm;

    /**
     * 出价成功率%
     */
    private BigDecimal bidSuccessRate;

    /**
     * 日志文件个数
     */
    private Integer logFileCount;

    /**
     * 3.20日志文件个数
     */
    private BigDecimal server320;

    /**
     * 175.56日志文件个数
     */
    private BigDecimal server17556;

}

