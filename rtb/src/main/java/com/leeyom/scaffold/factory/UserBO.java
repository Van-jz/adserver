package com.leeyom.scaffold.factory;

import lombok.Data;

@Data
public class UserBO {


    /**
     * 国家
     */
    private String country;

    /**
     * 区域
     */
    private String region;


    /**
     * 终端类型：Android 、IOS
     */
    private String osType;

    /**
     * 用户性别：男M、女F
     */
    private String gender;


    /**
     * 用户年纪
     */
    private Integer age;

}
