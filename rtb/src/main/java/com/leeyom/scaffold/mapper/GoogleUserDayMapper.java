package com.leeyom.scaffold.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.leeyom.scaffold.domain.entity.GoogleUserDay;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 谷歌日用户信息 Mapper 接口
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface GoogleUserDayMapper extends BaseMapper<GoogleUserDay> {

    Integer batchInsert(List<GoogleUserDay> list);

    Long countGuidByDay(@Param("day") String day);
}
