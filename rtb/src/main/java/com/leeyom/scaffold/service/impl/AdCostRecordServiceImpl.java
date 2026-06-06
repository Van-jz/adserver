package com.leeyom.scaffold.service.impl;

import com.baomidou.mybatisplus.core.toolkit.CollectionUtils;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.leeyom.scaffold.domain.entity.AdCostRecord;
import com.leeyom.scaffold.domain.vo.AdCostDayTotalVO;
import com.leeyom.scaffold.mapper.AdCostRecordMapper;
import com.leeyom.scaffold.service.IAdCostRecordService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AdCostRecordServiceImpl extends ServiceImpl<AdCostRecordMapper, AdCostRecord> implements IAdCostRecordService {

    @Override
    public AdCostDayTotalVO queryTotal(String day) {
        return getBaseMapper().selectSumByDay(day);
    }

    @Override
    public Integer batchInsert(List<AdCostRecord> list) {
        if (CollectionUtils.isEmpty(list)) {
            return 0;
        }
        return getBaseMapper().batchInsert(list);
    }
}
