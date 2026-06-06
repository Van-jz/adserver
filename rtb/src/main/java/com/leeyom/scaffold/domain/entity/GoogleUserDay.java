package com.leeyom.scaffold.domain.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;


/**
 * <p>
 * 谷歌日用户信息
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@TableName("google_user_day")
public class GoogleUserDay{


    /** google用户id */
    private String guid;

    /** 日期，yyyy-MM-dd */
    private String day;

}
