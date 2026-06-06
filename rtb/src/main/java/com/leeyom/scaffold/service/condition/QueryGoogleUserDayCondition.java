package com.leeyom.scaffold.service.condition;

import lombok.Data;
import lombok.ToString;

import java.io.Serializable;


/**
 * <p>
 * 谷歌日用户信息 查询条件
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@ToString
public class QueryGoogleUserDayCondition extends BaseCondition implements Serializable{
    private static final long serialVersionUID = 1L;

    /**
     * google用户id
     */
    private String guid;

    /**
     * 日期，yyyy-MM-dd
     */
    private String day;

}

