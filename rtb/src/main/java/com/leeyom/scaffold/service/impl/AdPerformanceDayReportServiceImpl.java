package com.leeyom.scaffold.service.impl;

import com.baomidou.mybatisplus.core.toolkit.CollectionUtils;
import com.baomidou.mybatisplus.extension.conditions.query.LambdaQueryChainWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.domain.entity.AdPerformanceDayReport;
import com.leeyom.scaffold.mapper.AdPerformanceDayReportMapper;
import com.leeyom.scaffold.service.IAdPerformanceDayReportService;
import com.leeyom.scaffold.service.condition.QueryAdPerformanceDayReportCondition;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 广告消耗日报 服务实现类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Service
public class AdPerformanceDayReportServiceImpl extends ServiceImpl<AdPerformanceDayReportMapper, AdPerformanceDayReport> implements IAdPerformanceDayReportService {


    @Override
    public PageInfo<AdPerformanceDayReport> pageInfo(QueryAdPerformanceDayReportCondition condition) {
        PageHelper.startPage(condition.getPageNum(), condition.getPageSize());
        LambdaQueryChainWrapper<AdPerformanceDayReport> query = buildWrapper(condition);
        List<AdPerformanceDayReport> list = query.list();
        return new PageInfo<>(list);
    }

    @Override
    public List<AdPerformanceDayReport> queryAllByCondition(QueryAdPerformanceDayReportCondition condition) {
        LambdaQueryChainWrapper<AdPerformanceDayReport> query = buildWrapper(condition);
        return query.list();
    }

    @Override
    public Integer batchInsert(List<AdPerformanceDayReport> list) {
        if (CollectionUtils.isEmpty(list)) {
            return 0;
        }
        return getBaseMapper().batchInsert(list);
    }


    private LambdaQueryChainWrapper<AdPerformanceDayReport> buildWrapper(QueryAdPerformanceDayReportCondition condition) {
        LambdaQueryChainWrapper<AdPerformanceDayReport> query = lambdaQuery();
        if (condition.getDate() != null) {
            query.eq(AdPerformanceDayReport::getDate, condition.getDate());
        }
        if (condition.getBidTimes() != null) {
            query.eq(AdPerformanceDayReport::getBidTimes, condition.getBidTimes());
        }
        if (condition.getImpressions() != null) {
            query.eq(AdPerformanceDayReport::getImpressions, condition.getImpressions());
        }
        if (condition.getSpend() != null) {
            query.eq(AdPerformanceDayReport::getSpend, condition.getSpend());
        }
        if (condition.getAvgCpm() != null) {
            query.eq(AdPerformanceDayReport::getAvgCpm, condition.getAvgCpm());
        }
        if (condition.getBidSuccessRate() != null) {
            query.eq(AdPerformanceDayReport::getBidSuccessRate, condition.getBidSuccessRate());
        }
        if (condition.getLogFileCount() != null) {
            query.eq(AdPerformanceDayReport::getLogFileCount, condition.getLogFileCount());
        }
        if (condition.getServer320() != null) {
            query.eq(AdPerformanceDayReport::getServer320, condition.getServer320());
        }
        if (condition.getServer17556() != null) {
            query.eq(AdPerformanceDayReport::getServer17556, condition.getServer17556());
        }
        return query;
    }
}
