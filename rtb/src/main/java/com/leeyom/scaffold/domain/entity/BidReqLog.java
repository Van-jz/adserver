package com.leeyom.scaffold.domain.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.extension.activerecord.Model;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * (User)
 *
 * @author luoxun
 * @since 2025-05-30 16:17:33
 */
@Data
public class BidReqLog extends Model<BidReqLog> implements Serializable {

    /**
     * 主键ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 请求id
     */
    @TableField("req_id")
    private String reqId;

    /**
     * 请求参数内容
     */
    @TableField("content")
    private String content;


    /**
     * 创建时间
     */
    @TableField("create_time")
    private Date createTime;
    /**
     * 获取主键值
     *
     * @return 主键值
     */
    @Override
    protected Serializable pkVal() {
        return this.id;
    }
}