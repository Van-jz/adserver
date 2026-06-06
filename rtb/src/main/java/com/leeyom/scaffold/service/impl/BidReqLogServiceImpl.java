package com.leeyom.scaffold.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.leeyom.scaffold.domain.entity.BidReqLog;
import com.leeyom.scaffold.mapper.BidReqLogMapper;
import com.leeyom.scaffold.service.BidReqLogService;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Date;

/**
 * (User)表服务实现类
 *
 * @author Leeyom Wang
 * @since 2020-05-30 16:17:36
 */
@Service
public class BidReqLogServiceImpl extends ServiceImpl<BidReqLogMapper, BidReqLog> implements BidReqLogService {

    @Override
    public BidReqLog save(String reqId, String content) {
        BidReqLog bidReqLog = new BidReqLog();
        bidReqLog.setReqId(reqId);
        bidReqLog.setContent(content);
        bidReqLog.setCreateTime(new Date());
        super.save(bidReqLog);
        return bidReqLog;
    }
}