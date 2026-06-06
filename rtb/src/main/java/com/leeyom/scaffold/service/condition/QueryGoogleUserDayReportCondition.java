package com.leeyom.scaffold.service.condition;

import lombok.Data;
import lombok.ToString;

import java.io.Serializable;


/**
 * <p>
 * 谷歌用户信息日报 查询条件
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@ToString
public class QueryGoogleUserDayReportCondition extends BaseCondition implements Serializable{
    private static final long serialVersionUID = 1L;

    /**
     * 统计日期，yyyy-MM-dd
     */
    private String day;

    /**
     * 用户去重总数
     */
    private Long guidTotal;

    /**
     * 当日用户去重总数
     */
    private Long todayGuidTotal;

    /**
     * 日增总数
     */
    private Long dayIncrease;

}

