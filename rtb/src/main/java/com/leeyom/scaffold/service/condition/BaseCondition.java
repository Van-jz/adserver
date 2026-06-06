package com.leeyom.scaffold.service.condition;

import lombok.Data;
import lombok.ToString;

import javax.validation.constraints.NotNull;

/**
 * <p>
 * 基础查询条件
 * </p>
 *
 * @author luoxun
 * @since 2024-08-04
 */
@Data
@ToString
public class BaseCondition {

    @NotNull(message = "当前页不能为空")
    private Integer pageNum;

    @NotNull(message = "页大小不能为空")
    private Integer pageSize;
}
