package com.leeyom.scaffold.factory;

import lombok.Data;

import java.util.List;

/**
 * 投放策略，如果参数为空，则代表该参数不参与挑选策略
 */
@Data
public class StrategyParam {

    /**
     * 投放国家列表
     */
    private List<String> countryList;

    /**
     * 投放区域列表
     */
    private List<String> regionList;

    /**
     * 投放终端类型：Android 、IOS
     */
    private List<String> osTypeList;

    /**
     * 投放用户性别：M、F
     */
    private List<String> genderList;


    /**
     * 投放用户年纪最小值
     */
    private Integer ageMin;

    /**
     * 投放用户年纪最大值
     */
    private Integer ageMax;

}
