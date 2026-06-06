package com.leeyom.scaffold.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.leeyom.scaffold.domain.entity.AdPerformanceDayReport;

import java.util.List;

/**
 * <p>
 * 广告消耗日报 Mapper 接口
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface AdPerformanceDayReportMapper extends BaseMapper<AdPerformanceDayReport> {

    Integer batchInsert(List<AdPerformanceDayReport> list);

}
