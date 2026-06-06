package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.service.condition.QueryGoogleUserDayCondition;
import com.leeyom.scaffold.domain.entity.GoogleUserDay;

import java.util.List;

/**
 * <p>
 * 谷歌日用户信息 服务类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface IGoogleUserDayService extends IService<GoogleUserDay> {

    /**
     * 查询唯一
     * @return
     */
    GoogleUserDay queryOneByUniqDayGuid( String guid, String day);

    /**
    * 分页查询
    * @param condition
    * @return
    */
    PageInfo<GoogleUserDay> pageInfo(QueryGoogleUserDayCondition condition);

    /**
     * 查询全部（根据查询条件）
     * @param condition
     * @return
     */
    List<GoogleUserDay> queryAllByCondition(QueryGoogleUserDayCondition condition);


    /**
     * 批量插入
     * @param list
     * @return
     */
    Integer batchInsert(List<GoogleUserDay> list);

}
