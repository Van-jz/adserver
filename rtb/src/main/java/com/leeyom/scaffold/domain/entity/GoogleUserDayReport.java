package com.leeyom.scaffold.domain.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;


/**
 * <p>
 * 谷歌用户信息日报
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@TableName("google_user_day_report")
public class GoogleUserDayReport{


    /** 统计日期，yyyy-MM-dd */
    private String day;

    /** 用户去重总数 */
    private Long guidTotal;

    /** 当日用户去重总数 */
    private Long todayGuidTotal;

    /** 日增总数 */
    private Long dayIncrease;

}
