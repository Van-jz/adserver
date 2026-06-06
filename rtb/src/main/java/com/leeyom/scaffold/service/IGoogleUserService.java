package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.github.pagehelper.PageInfo;
import com.leeyom.scaffold.domain.entity.GoogleUser;
import com.leeyom.scaffold.domain.vo.GuidByDayVO;
import com.leeyom.scaffold.service.condition.QueryGoogleUserCondition;

import java.util.List;

/**
 * <p>
 * 谷歌用户信息 服务类
 * </p>
 *
 * @author luoxun
 * @date 2025-09-16
 */
public interface IGoogleUserService extends IService<GoogleUser> {

    /**
     * 查询唯一
     * @return
     */
    GoogleUser queryOneByUniqGuid( String guid);

    /**
    * 分页查询
    * @param condition
    * @return
    */
    PageInfo<GoogleUser> pageInfo(QueryGoogleUserCondition condition);

    /**
     * 查询全部（根据查询条件）
     * @param condition
     * @return
     */
    List<GoogleUser> queryAllByCondition(QueryGoogleUserCondition condition);

    /**
     * 批量插入
     * @param list
     * @return
     */
    Integer batchInsert(List<GoogleUser> list);

    GuidByDayVO queryGuid(String day);
}
