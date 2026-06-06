package com.leeyom.scaffold.domain.vo;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AdCostDayTotalVO {

    private BigDecimal totalCost;
    private Integer rowNumber;

}
