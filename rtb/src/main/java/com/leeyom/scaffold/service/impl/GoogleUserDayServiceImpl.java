package com.leeyom.scaffold.service.impl;

import com.aliyun.oss.ServiceException;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.CollectionUtils;
import com.baomidou.mybatisplus.extension.conditions.query.LambdaQueryChainWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;

import com.leeyom.scaffold.service.condition.QueryGoogleUserDayCondition;
import com.leeyom.scaffold.domain.entity.GoogleUserDay;
import com.leeyom.scaffold.mapper.GoogleUserDayMapper;
import com.leeyom.scaffold.service.IGoogleUserDayService;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * <p>
 * 谷歌日用户信息 服务实现类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Service
public class GoogleUserDayServiceImpl extends ServiceImpl<GoogleUserDayMapper, GoogleUserDay> implements IGoogleUserDayService {

    @Override
    public GoogleUserDay queryOneByUniqDayGuid( String guid, String day) {
        if ( StringUtils.isBlank(guid) || StringUtils.isBlank(day) ) {
            throw new ServiceException("参数不能存在为空的数据");
        }
        LambdaQueryChainWrapper<GoogleUserDay> query = lambdaQuery();
        query.eq(GoogleUserDay::getGuid, guid);
        query.eq(GoogleUserDay::getDay, day);
        return query.one();
    }

    @Override
    public PageInfo<GoogleUserDay> pageInfo(QueryGoogleUserDayCondition condition) {
        PageHelper.startPage(condition.getPageNum(), condition.getPageSize());
        LambdaQueryChainWrapper<GoogleUserDay> query = buildWrapper(condition);
        List<GoogleUserDay> list = query.list();
        return new PageInfo<>(list);
    }

    @Override
    public List<GoogleUserDay> queryAllByCondition(QueryGoogleUserDayCondition condition) {
        LambdaQueryChainWrapper<GoogleUserDay> query = buildWrapper(condition);
        return query.list();
    }


    @Override
    @Transactional
    public Integer batchInsert(List<GoogleUserDay> list) {
        if (CollectionUtils.isEmpty(list)) {
            return 0;
        }
        return getBaseMapper().batchInsert(list);
    }

    private LambdaQueryChainWrapper<GoogleUserDay> buildWrapper(QueryGoogleUserDayCondition condition) {
        LambdaQueryChainWrapper<GoogleUserDay> query = lambdaQuery();
        if (StringUtils.isNotBlank(condition.getGuid())) {
            query.like(GoogleUserDay::getGuid, "%" + condition.getGuid() + "%");
        }
        if (StringUtils.isNotBlank(condition.getDay())) {
            query.like(GoogleUserDay::getDay, "%" + condition.getDay() + "%");
        }
        return query;
    }
}
