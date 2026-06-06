package com.leeyom.scaffold.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.leeyom.scaffold.domain.entity.AdCostRecord;
import com.leeyom.scaffold.domain.vo.AdCostDayTotalVO;

import java.math.BigDecimal;
import java.util.List;

/**
 * <p>
 * 广告消耗日报 Mapper 接口
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface AdCostRecordMapper extends BaseMapper<AdCostRecord> {

    Integer batchInsert(List<AdCostRecord> list);

    AdCostDayTotalVO selectSumByDay(String day);
}
