package com.leeyom.scaffold.domain.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.util.Date;


/**
 * <p>
 * 广告消耗日报
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@TableName("ad_performance_day_report")
public class AdPerformanceDayReport{


    /** 日期 */
    private Date date;

    /** 出价次数 */
    private Integer bidTimes;

    /** 曝光次数 */
    private Integer impressions;

    /** 消耗 */
    private BigDecimal spend;

    /** 平均CPM */
    private BigDecimal avgCpm;

    /** 出价成功率% */
    private BigDecimal bidSuccessRate;

    /** 日志文件个数 */
    private Integer logFileCount;

    /** 3.20日志文件个数 */
    private BigDecimal server320;

    /** 175.56日志文件个数 */
    private BigDecimal server17556;

}
