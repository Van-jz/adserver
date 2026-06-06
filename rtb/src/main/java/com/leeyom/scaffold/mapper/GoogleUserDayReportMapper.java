package com.leeyom.scaffold.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.leeyom.scaffold.domain.entity.GoogleUserDayReport;

import java.util.List;

/**
 * <p>
 * 谷歌用户信息日报 Mapper 接口
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface GoogleUserDayReportMapper extends BaseMapper<GoogleUserDayReport> {

    Integer batchInsert(List<GoogleUserDayReport> list);

}
