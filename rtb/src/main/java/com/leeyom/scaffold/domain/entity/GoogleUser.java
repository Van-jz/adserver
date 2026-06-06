package com.leeyom.scaffold.domain.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;


/**
 * <p>
 * 谷歌用户信息
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Data
@TableName("google_user")
public class GoogleUser{


    /** google用户id */
    private String guid;

    /** 新增日期，yyyy-MM-dd */
    private String day;

}
