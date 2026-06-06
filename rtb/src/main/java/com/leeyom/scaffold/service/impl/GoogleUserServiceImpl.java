package com.leeyom.scaffold.service.impl;

import com.aliyun.oss.ServiceException;
import com.baomidou.mybatisplus.extension.conditions.query.LambdaQueryChainWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.domain.entity.GoogleUser;
import com.leeyom.scaffold.domain.vo.GuidByDayVO;
import com.leeyom.scaffold.mapper.GoogleUserDayMapper;
import com.leeyom.scaffold.mapper.GoogleUserMapper;
import com.leeyom.scaffold.service.IGoogleUserService;
import com.leeyom.scaffold.service.condition.QueryGoogleUserCondition;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import javax.annotation.Resource;
import java.util.List;

/**
 * <p>
 * 谷歌用户信息 服务实现类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
@Service
public class GoogleUserServiceImpl extends ServiceImpl<GoogleUserMapper, GoogleUser> implements IGoogleUserService {

    @Resource
    private GoogleUserDayMapper googleUserDayMapper;

    @Override
    public GoogleUser queryOneByUniqGuid(String guid) {
        if (StringUtils.isBlank(guid)) {
            throw new ServiceException("参数不能存在为空的数据");
        }
        LambdaQueryChainWrapper<GoogleUser> query = lambdaQuery();
        query.eq(GoogleUser::getGuid, guid);
        return query.one();
    }

    @Override
    public PageInfo<GoogleUser> pageInfo(QueryGoogleUserCondition condition) {
        PageHelper.startPage(condition.getPageNum(), condition.getPageSize());
        LambdaQueryChainWrapper<GoogleUser> query = buildWrapper(condition);
        List<GoogleUser> list = query.list();
        return new PageInfo<>(list);
    }

    @Override
    public List<GoogleUser> queryAllByCondition(QueryGoogleUserCondition condition) {
        LambdaQueryChainWrapper<GoogleUser> query = buildWrapper(condition);
        return query.list();
    }

    @Override
    @Transactional
    public Integer batchInsert(List<GoogleUser> list) {
        if (CollectionUtils.isEmpty(list)) {
            return 0;
        }
        return getBaseMapper().batchInsert(list);
    }

    @Override
    public GuidByDayVO queryGuid(String day) {
        GuidByDayVO vo = new GuidByDayVO();
        vo.setGuidAddByAllDay(getBaseMapper().countGuidByDay(day));
        vo.setGuidAddByDay(googleUserDayMapper.countGuidByDay(day));
        return vo;
    }

    private LambdaQueryChainWrapper<GoogleUser> buildWrapper(QueryGoogleUserCondition condition) {
        LambdaQueryChainWrapper<GoogleUser> query = lambdaQuery();
        if (StringUtils.isNotBlank(condition.getGuid())) {
            query.like(GoogleUser::getGuid, "%" + condition.getGuid() + "%");
        }
        if (StringUtils.isNotBlank(condition.getDay())) {
            query.like(GoogleUser::getDay, "%" + condition.getDay() + "%");
        }
        return query;
    }
}
