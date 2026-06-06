package com.leeyom.scaffold.enums;

import com.baomidou.mybatisplus.annotation.IEnum;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.leeyom.scaffold.common.exception.BizException;
import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * <p>
 * 广告筛选策略 业务枚举类
 * </p>
 *
 * @author luoxun
 * @date 2025-04-01
 */
@AllArgsConstructor
@Getter
@JsonFormat(shape = JsonFormat.Shape.OBJECT)
public enum AdvChoiceStrategyEnum implements IEnum<String> {

    BID_ONE_PER_1000("bid_one_per_1000", "1000次请求竞价一次"),
    FILTER_BY_CRITERIA("filter_by_criteria", "按条件筛选"),
    ;
    private String value;
    private String name;

    public static boolean isValid(String value) {
        for (AdvChoiceStrategyEnum item : AdvChoiceStrategyEnum.values()) {
            if (item.getValue().equalsIgnoreCase(value)) {
                return true;
            }
        }
        return false;
    }

    public static AdvChoiceStrategyEnum parse(String value) {
        for (AdvChoiceStrategyEnum item : AdvChoiceStrategyEnum.values()) {
            if (item.getValue().equalsIgnoreCase(value)) {
                return item;
            }
        }
        throw new BizException("参数错误");
    }

}
