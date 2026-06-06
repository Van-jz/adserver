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
@TableName("ad_cost_record")
public class AdCostRecord {

    private Long id;

    private String day;

    private String bidid;

    private String adid;

    private BigDecimal price;


}
