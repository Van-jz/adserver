package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.service.condition.QueryAdPerformanceDayReportCondition;
import com.leeyom.scaffold.domain.entity.AdPerformanceDayReport;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 广告消耗日报 服务类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface IAdPerformanceDayReportService extends IService<AdPerformanceDayReport> {


    /**
    * 分页查询
    * @param condition
    * @return
    */
    PageInfo<AdPerformanceDayReport> pageInfo(QueryAdPerformanceDayReportCondition condition);

    /**
     * 查询全部（根据查询条件）
     * @param condition
     * @return
     */
    List<AdPerformanceDayReport> queryAllByCondition(QueryAdPerformanceDayReportCondition condition);

    /**
     * 批量插入
     * @param list
     * @return
     */
    Integer batchInsert(List<AdPerformanceDayReport> list);

}
