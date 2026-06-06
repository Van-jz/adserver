package com.leeyom.scaffold.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.leeyom.scaffold.domain.entity.BidReqLog;

/**
 * (User)表服务接口
 *
 * @author Leeyom Wang
 * @since 2020-05-30 16:17:36
 */
public interface BidReqLogService extends IService<BidReqLog> {

    /**
     * @param reqId
     * @param content
     */
    BidReqLog save(String reqId, String content);
}