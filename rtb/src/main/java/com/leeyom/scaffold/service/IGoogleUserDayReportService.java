package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.service.condition.QueryGoogleUserDayReportCondition;
import com.leeyom.scaffold.domain.entity.GoogleUserDayReport;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 谷歌用户信息日报 服务类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface IGoogleUserDayReportService extends IService<GoogleUserDayReport> {


    /**
    * 分页查询
    * @param condition
    * @return
    */
    PageInfo<GoogleUserDayReport> pageInfo(QueryGoogleUserDayReportCondition condition);

    /**
     * 查询全部（根据查询条件）
     * @param condition
     * @return
     */
    List<GoogleUserDayReport> queryAllByCondition(QueryGoogleUserDayReportCondition condition);


    /**
     * 批量插入
     * @param list
     * @return
     */
    Integer batchInsert(List<GoogleUserDayReport> list);

}
