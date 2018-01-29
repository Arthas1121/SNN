import tensorflow as tf
from random import *
import math

class Layer(object):
    def __init__(self,input,n_in,n_out,sess, W=None):
        self.input = input
        self.n_in = n_in
        self.n_out = n_out
        if W is None:
            W = tf.Variable(tf.random_normal([n_in,n_out], 1, .5, tf.float32))
        i = tf.Variable(0)
        sum_z = tf.Variable(tf.zeros([n_out,n_in],tf.float32))
        sum_W = tf.Variable(tf.zeros([n_out,n_in],tf.float32))
        c_zero = tf.constant(0.,tf.float32)
        c_one = tf.constant(1.,tf.float32)
        
        init = tf.global_variables_initializer()
        
        sess.run(init)
        
        self.W = W
        self.i = i
        self.sum_z = sum_z
        self.sum_W = sum_W
        self.c_zero = c_zero
        self.c_one = c_one
        def cal_out():
            r, ind = tf.nn.top_k(self.input, self.n_in)
            r_ind = tf.reverse(ind,[0])
            nx = tf.gather(self.input,r_ind)
            nW = tf.transpose(tf.gather(self.W,r_ind))
            nxW = tf.multiply(nx, nW)
            
            def body_z(i,z):
                z = tf.slice(
                    tf.concat(
                        [
                            tf.cast(
                                tf.reduce_sum(
                                    tf.slice(nxW,[0,0],[self.n_out,i+1]),
                                    1,True),
                                tf.float32),
                            z],
                        1),
                    [0,0],[self.n_out,self.n_in])
                return [i+1,z]
            
            def body_W(i,z):
                z = tf.slice(
                    tf.concat(
                        [
                            tf.cast(
                                tf.reduce_sum(
                                    tf.slice(nW,[0,0],[self.n_out,i+1]),
                                    1,True),
                                tf.float32),
                            z],
                        1),
                    [0,0],[self.n_out,self.n_in])
                return [i+1,z]

            def condition(i,z):
                return i<self.n_in
            
            r1,n_sum_z=tf.while_loop(condition, body_z, [self.i,self.sum_z])
            r2,n_sum_W=tf.while_loop(condition, body_W, [self.i,self.sum_W])
            f_sum_z = tf.reverse(n_sum_z,[1])
            f_sum_W = tf.reverse(n_sum_W,[1])
            
            out_all = tf.divide(f_sum_z, tf.subtract(f_sum_W,1))
            out_all_2 = tf.concat(
                [
                    out_all,
                    tf.transpose(
                        [
                            tf.tile(
                                [tf.divide(self.c_one,self.c_zero)],
                                [self.n_out])
                            ]
                        )
                    ]
                ,1)
            
            out_ok = tf.where(
                tf.logical_and(
                    tf.less(
                        tf.cast(
                            tf.tile(
                                [tf.concat([nx,[1]],0)],
                                [self.n_out,1]),
                            tf.float32)
                        ,
                        out_all_2),
                    tf.greater_equal(
                        tf.cast(
                            tf.tile(
                                [tf.slice(
                                    tf.concat(
                                        [nx,[tf.divide(self.c_one,self.c_zero),tf.divide(self.c_one,self.c_zero)]],0),
                                    [1],
                                    [self.n_in+1])
                                    ],
                                [self.n_out,1]),
                            tf.float32),
                        out_all_2)))

            out_idx = tf.transpose(tf.concat([[tf.range(0,self.n_out)],[tf.cast(tf.segment_min(out_ok[:, 1], out_ok[:, 0]),tf.int32)]],0))
            out = tf.gather_nd(out_all_2,out_idx)
            return out
        self.output = cal_out()

def w_sum_cost(W):
    zero_colume = tf.zeros([tf.shape(W)[0],1],tf.float32)
    sum_weight = tf.reduce_sum(W, 1, True)
    sum_weight_sub = tf.subtract(1., sum_weight)
    sum_weight_all = tf.reduce_max(tf.concat([zero_colume,sum_weight_sub], 1), 1,True)
    cost = tf.reduce_sum(sum_weight_all, 0, False)
    return cost

def loss_func(output,true_index):
    z1 = tf.exp(tf.subtract(0., output[true_index]))
    z2 = tf.reduce_sum(tf.exp(tf.subtract(0., output)), 0, False)
    loss = tf.log(tf.divide(z1,z2))
    return loss

def L2_func(W):
    w_sqr = tf.square(W)
    W2 = tf.reduce_sum(w_sqr)
    return W2
        
if __name__ == '__main__':
    
    K = 10.
    K2 = 0.
    training_epochs = 1000
    learning_rate = 0.1
    
    sess = tf.Session()
    input = tf.placeholder(tf.float32)
    
    l1 = Layer(input,2,4,sess)
    l2 = Layer(l1.output,4,2,sess)
    
    def cost_func(true_index):
        return tf.reduce_sum([[loss_func(l2.output,true_index)],tf.multiply(K, w_sum_cost(l1.W)),tf.multiply(K, w_sum_cost(l2.W)),[tf.multiply(K2, L2_func(l1.W))],[tf.multiply(K2, L2_func(l2.W))]])
    
    print('start training...')
    
    for epoch in range(training_epochs):
        train_input = [randint(0,1),randint(0,1)]
        if train_input[0] == train_input[1]:
            train_output = 0
        else:
            train_output = 1
        train_input = [math.exp(train_input[0]),math.exp(train_input[1])]
        if epoch % 1 == 0:
            print('epoch '+repr(epoch)+', cost = '+repr(sess.run(cost_func(train_output),{input:train_input})))
        #print('i0: '+repr(train_input[0])+' i1: '+repr(train_input[1])+' o: '+repr(train_output))
        g_W1,g_W2 = tf.gradients(cost_func(train_output),[l1.W,l2.W])
        n_g_W1 = tf.where(tf.is_nan(g_W1.values),tf.multiply(tf.ones_like(g_W1.values),1),g_W1.values)
        n_g_W2 = tf.where(tf.is_nan(g_W2.values),tf.multiply(tf.ones_like(g_W2.values),1),g_W2.values)
        f_g_W1 = tf.multiply(tf.cond(tf.equal(0.,tf.reduce_sum(n_g_W1)),lambda:tf.divide(n_g_W1,1.),lambda:tf.divide(n_g_W1,tf.reduce_sum(n_g_W1))),learning_rate)
        f_g_W2 = tf.multiply(tf.cond(tf.equal(0.,tf.reduce_sum(n_g_W2)),lambda:tf.divide(n_g_W2,1.),lambda:tf.divide(n_g_W2,tf.reduce_sum(n_g_W2))),learning_rate)
        
        #print(sess.run(n_g_W1,{input:train_input}))
        #print(sess.run(n_g_W2,{input:train_input}))
        
        print(sess.run(f_g_W1,{input:train_input}))
        print(sess.run(f_g_W2,{input:train_input}))
        
        print(sess.run(tf.scatter_sub(l1.W,g_W1.indices,f_g_W1),{input:train_input}))
        print(sess.run(tf.scatter_sub(l2.W,g_W2.indices,f_g_W2),{input:train_input}))
    
    print(sess.run(l1.W))
    print(sess.run(l2.W))
    