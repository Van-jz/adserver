package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.leeyom.scaffold.domain.entity.AdCostRecord;
import com.leeyom.scaffold.domain.vo.AdCostDayTotalVO;

import java.util.List;

/**
 * <p>
 * 广告消耗日报 服务类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface IAdCostRecordService extends IService<AdCostRecord> {


    AdCostDayTotalVO queryTotal(String day);

    /**
     * 批量插入
     * @param list
     * @return
     */
    Integer batchInsert(List<AdCostRecord> list);

}
