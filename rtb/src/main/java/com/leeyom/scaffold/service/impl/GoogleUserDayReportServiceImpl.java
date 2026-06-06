package com.leeyom.scaffold.service.impl;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.conditions.query.LambdaQueryChainWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;

import com.leeyom.scaffold.service.condition.QueryGoogleUserDayReportCondition;
import com.leeyom.scaffold.domain.entity.GoogleUserDayReport;
import com.leeyom.scaffold.mapper.GoogleUserDayReportMapper;
import com.leeyom.scaffold.service.IGoogleUserDayReportService;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * <p>
 * 谷歌用户信息日报 服务实现类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Service
public class GoogleUserDayReportServiceImpl extends ServiceImpl<GoogleUserDayReportMapper, GoogleUserDayReport> implements IGoogleUserDayReportService {


    @Override
    public PageInfo<GoogleUserDayReport> pageInfo(QueryGoogleUserDayReportCondition condition) {
        PageHelper.startPage(condition.getPageNum(), condition.getPageSize());
        LambdaQueryChainWrapper<GoogleUserDayReport> query = buildWrapper(condition);
        List<GoogleUserDayReport> list = query.list();
        return new PageInfo<>(list);
    }

    @Override
    public List<GoogleUserDayReport> queryAllByCondition(QueryGoogleUserDayReportCondition condition) {
        LambdaQueryChainWrapper<GoogleUserDayReport> query = buildWrapper(condition);
        return query.list();
    }


    @Override
    public Integer batchInsert(List<GoogleUserDayReport> list) {
        if (CollectionUtils.isEmpty(list)) {
            return 0;
        }
        return getBaseMapper().batchInsert(list);
    }

    private LambdaQueryChainWrapper<GoogleUserDayReport> buildWrapper(QueryGoogleUserDayReportCondition condition) {
        LambdaQueryChainWrapper<GoogleUserDayReport> query = lambdaQuery();
        if (StringUtils.isNotBlank(condition.getDay())) {
            query.like(GoogleUserDayReport::getDay, "%" + condition.getDay() + "%");
        }
        if (condition.getGuidTotal() != null) {
            query.eq(GoogleUserDayReport::getGuidTotal, condition.getGuidTotal());
        }
        if (condition.getTodayGuidTotal() != null) {
            query.eq(GoogleUserDayReport::getTodayGuidTotal, condition.getTodayGuidTotal());
        }
        if (condition.getDayIncrease() != null) {
            query.eq(GoogleUserDayReport::getDayIncrease, condition.getDayIncrease());
        }
        return query;
    }
}
